# encoding: utf-8
"""
Defines s3Repo plugin. See docstring for s3Repo class.

Author: Clayton Burlison <https://clburlison.com>
Source: https://github.com/clburlison/Munki-s3Repo-Plugin
"""

# Cheat to define mac/non-mac runs
try:
    from Foundation import CFPreferencesCopyAppValue
    from PyObjCTools import Conversion
    platform = 'macos'
except(ImportError):
    platform = 'non-mac'

from munkilib.munkirepo import Repo
import tempfile
import io
import os
import sys
import threading

try:
    from boto3.s3.transfer import S3Transfer
    import boto3
    import botocore
except(ImportError):
    print('This plugin uses the boto3 module. Please install it with:\n'
          '   pip install boto3 --user')
    exit(1)

__version__ = '0.4.4'
BUNDLE = 'com.clburlison.munki.s3Repo'


def get_preferences(platform):
    """Return a dictonary of the preferences from the current profile key.

    If no profile is set the plugin will use the 'default' profile key.

    Multiple profiles to be set in the 'com.clburlison.munki.s3Repo'
    preference domain. Swithing between the profiles can be done by changing
    the S3REPO_PROFILE environment variable.
    """
    # If this is running on a non-mac platform cheat and use environment vars
    if platform == 'non-mac':
        if os.environ.get('bucket_name') is None:
            print("Environment variable 'bucket_name' is not set!")
            sys.exit(1)
        if os.environ.get('AWS_REGION') is None:
            print("Environment variable 'AWS_REGION' is not set!")
            sys.exit(1)
        prefs = {
            'bucket': os.environ.get('bucket_name'),
            'region': os.environ.get('AWS_REGION'),
         }
        return prefs

    profile = os.environ.get('S3REPO_PROFILE') or 'default'
    if profile is not 'default':
        print("DEBUG: Currently using the '{}' profile".format(profile))
    pref = CFPreferencesCopyAppValue(profile, BUNDLE)
    if pref is None:
        sys.stderr.write("ERROR: s3Repo plugin is not properly configured. \n"
                         "Please follow the setup guide: "
                         "https://github.com/clburlison/"
                         "Munki-s3Repo-Plugin#setup \n")
        exit(1)
    # Remove the AWS_PROFILE env variable. The s3Repo Plugin is overriding
    # all of these variables in the bot3.session and this can causes
    # issues if the profile is not properly set.
    try:
        del os.environ['AWS_PROFILE']
    except(KeyError):
        pass

    # Return a python dictonary of our preferences
    return Conversion.pythonCollectionFromPropertyList(pref)


class ProgressPercentage(object):
    """A handler for S3Transfer progress feedback.

    Based off https://goo.gl/SGqSt6 & https://goo.gl/zXVGrQ
    """

    def __init__(self, filename):
        """Constructor."""
        self._filename = filename
        self._size = float(os.path.getsize(filename))
        self._seen_so_far = 0
        self.prefix = 'Progress:'
        self.bar_length = 50
        self.str_format = "{0:.1f}"  # We only need one decimal place IE 57.4%
        self._lock = threading.Lock()

    def __call__(self, bytes_amount):
        """Write feedback to stdout as the file is transfered."""
        # To simplify we'll assume this is hooked up to a single filename.
        with self._lock:
            self._seen_so_far += bytes_amount
            # Amount comlete as a string percentage
            percents = self.str_format.format(
                100 * (self._seen_so_far / self._size))
            filled_length = int(round(
                self.bar_length * self._seen_so_far / float(self._size)))
            bar = '█' * filled_length + '-' * (self.bar_length - filled_length)

            # Write out the progress bar
            sys.stdout.write('\r%s |%s| %s%s' % (self.prefix, bar,
                                                 percents, '%'))

            # When at complete return the cursor to the start of a new line
            if self._seen_so_far == self._size:
                sys.stdout.write('\n')
            sys.stdout.flush()


class BotoError(Exception):
    """Generic exception for all boto3 errors.

    This should only be used for non-recoverable errors that require an exit.
    """

    def __init__(self, message, error):
        """Constructor."""
        # Call the base class constructor with the parameters it needs
        super(BotoError, self).__init__(message)
        super(BotoError, self).__init__(error)
        print('BotoError: {}.\n           {}'.format(message, error))
        exit(1)


class s3Repo(Repo):
    """Override class for a munkirepo plugin."""

    def __init__(self, baseurl):
        """Constructor."""
        print("s3Repo Plugin platform is '{}'".format(platform))
        prefs = get_preferences(platform)
        endpoint_url = prefs.get('endpoint_url')
        self.BUCKET_NAME = prefs.get('bucket')
        self.EXTRA_ARGS = prefs.get('ExtraArgs')
        if prefs.get('aws_access_key_id'):
            session = boto3.session.Session(
                    aws_access_key_id=prefs.get('aws_access_key_id'),
                    aws_secret_access_key=prefs.get('aws_secret_access_key'),
                    region_name=prefs.get('region'),
                    )
        else:
            session = boto3.session.Session(region_name=prefs.get('region'))
        # If using minio or another S3 compatible solution the endpoint_url
        # key needs to be set however we can pass None if the pref isn't set.
        self.s3 = session.resource(
            service_name='s3', endpoint_url=endpoint_url)
        self.client = session.client(
            service_name='s3', endpoint_url=endpoint_url)
        self.transfer = S3Transfer(self.client)
        self._connect()

    def _connect(self):
        """Check connection to a S3 bucket resource.

        Validates bucket connectivity and bucket existence before
        continuing the munki process. This uses the head method
        which is the most cost effective check.
        """
        try:
            self.s3.meta.client.head_bucket(Bucket=self.BUCKET_NAME)
        except(botocore.exceptions.ClientError) as err:
            raise BotoError(
                "S3 bucket '{}' has not been "
                "created".format(self.BUCKET_NAME), err)
        except(botocore.vendored.requests.exceptions.ConnectionError) as err:
            raise BotoError("Unable to connect to S3 bucket", err)
        except(botocore.exceptions.NoCredentialsError) as err:
            raise BotoError(err, "Please follow the setup guide: "
                            "https://github.com/clburlison/"
                            "Munki-s3Repo-Plugin#setup")
        except(botocore.exceptions.ParamValidationError) as err:
            raise BotoError("Repo URL is not set or is invalid. Please run "
                            "'munkiimport --configure' and set "
                            "the Repo URL to your S3 bucket name.",
                            err)
        except(Exception) as err:
            raise BotoError("An error occurred in '_connect' while attempting "
                            "to access the S3 bucket.", err)

    def itemlist(self, kind):
        """Return a list of resource_identifiers for each item of kind.

        Kind will be 'catalogs', 'manifests', 'pkgsinfo', 'pkgs', or 'icons'.
        For a file-backed repo this would be a list of pathnames.

        The returned file list string does not have the kind:
         - Good - apps/GoogleChrome-xxx.plist
         - Bad  - pkgs/apps/GoogleChrome-xxx.plist
        """
        file_list = []
        my_bucket = self.s3.Bucket(self.BUCKET_NAME)
        for obj in my_bucket.objects.all():
            obj_list = obj.key.split('/')
            # skip directories and files that start with a period
            if obj_list[0].startswith('.') or obj_list[-1].startswith('.'):
                continue
            if kind == obj_list[0]:
                # remove the first item, 'kind', from list
                del obj_list[0]
                # rejoin the list into a relative object path
                rel_path = '/'.join(obj_list)
                file_list.append(rel_path)

        return file_list

    def get(self, resource_identifier):
        """Download and return the remote content of an remote S3 item.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would return the contents of
        <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        Avoid using this method with the 'pkgs' kind as it might return a
        really large blob of data.
        """
        fileobj, directivepath = tempfile.mkstemp()
        try:
            self.transfer.download_file(bucket=self.BUCKET_NAME,
                                        key=resource_identifier,
                                        filename=directivepath)
            return open(directivepath).read()
        except(botocore.exceptions.ClientError) as err:
            print("DEBUG: The file '{}' does not exist. {}".format(
                  resource_identifier, err))
        except(Exception) as err:
            raise BotoError("An error occurred in 'get' while attempting "
                            "to download a file.", err)

    def get_to_local_file(self, resource_identifier, local_file_path):
        """Download content of a remote S3 item and save to a local file.

        For a file-backed repo, a resource_identifier
        of 'pkgsinfo/apps/Firefox-52.0.plist' would copy the contents of
        <repo_root>/pkgsinfo/apps/Firefox-52.0.plist to a local file given by
        local_file_path.
        """
        try:
            # TODO: Make ProgressPercentage() work with files when they are
            # downloaded via S3Transfer
            self.transfer.download_file(bucket=self.BUCKET_NAME,
                                        key=resource_identifier,
                                        filename=local_file_path)
        except(Exception) as err:
            raise BotoError("An error occurred in 'get_to_local_file' while "
                            "attempting to download a file.", err)

    def _extra_control(self, resource_identifier, extra_args):
        """Return ExtraArgs with correct cache age.

        This allows granular control over the storage class and cache of each
        file type.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would result in the resource of
        pkgsinfo which will then map to the 'pkgsinfo_age' pref key.
        """
        if extra_args is None:
            return {}
        prefs = get_preferences(platform)
        directory = resource_identifier.split('/')[0]
        cache_age = (prefs.get(directory + '_age')
                     or prefs.get('default_age'))
        storage_class = (prefs.get(directory + '_storage')
                         or prefs.get('default_class'))
        extra_args['Metadata']['Cache-Control'] = str(cache_age)
        extra_args['StorageClass'] = str(storage_class)
        return extra_args

    def put(self, resource_identifier, content):
        """Upload python data to the remote S3 bucket.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would result in the content being
        saved to <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        # boto3.client.upload_fileobj() needs data to be a binary object
        data = io.BytesIO(content)
        extra = self._extra_control(resource_identifier, self.EXTRA_ARGS)
        try:
            self.client.upload_fileobj(Fileobj=data,
                                       Bucket=self.BUCKET_NAME,
                                       Key=resource_identifier,
                                       ExtraArgs=extra)
        except(Exception) as err:
            raise BotoError("An error occurred in 'put' while attempting "
                            "to upload a file.", err)

    def put_from_local_file(self, resource_identifier, local_file_path):
        """Upload the content of local file to the remote S3 bucket.

        For a file-backed repo, a resource_identifier
        of 'pkgsinfo/apps/Firefox-52.0.plist' would result in the content
        being saved to <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        extra = self._extra_control(resource_identifier, self.EXTRA_ARGS)
        try:
            self.transfer.upload_file(filename=local_file_path,
                                      bucket=self.BUCKET_NAME,
                                      key=resource_identifier,
                                      extra_args=extra,
                                      callback=ProgressPercentage(
                                        local_file_path))
        except(Exception) as err:
            raise BotoError("An error occurred in 'put_from_local_file' while "
                            "attempting to upload a file.", err)

    def delete(self, resource_identifier):
        """Delete a repo object located by resource_identifier.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would result in the deletion of
        <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        try:
            self.client.delete_object(Bucket=self.BUCKET_NAME,
                                      Key=resource_identifier)
        except(Exception) as err:
            raise BotoError("An error occurred in 'delete' while attempting "
                            "to upload a file.", err)
