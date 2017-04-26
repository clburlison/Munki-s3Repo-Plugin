"""
Defines s3Repo plugin. See docstring for s3Repo class.

Author: Clayton Burlison <https://clburlison.com>
Source: https://github.com/clburlison/Munki-s3Repo-Plugin
"""
# encoding: utf-8

from Foundation import CFPreferencesCopyAppValue
from PyObjCTools import Conversion
from munkilib.munkirepo import Repo
import tempfile
import io
import os
import sys

try:
    import boto3
    import botocore
except(ImportError):
    print('This plugin uses the boto3 module. Please install it with:\n'
          '   pip install boto3 --user')

__version__ = '0.2.1'
BUNDLE = 'com.clburlison.munki.s3Repo'


def get_preferences():
    """Return a dictonary of the preferences from the current profile key.

    If no profile is set the plugin will use the 'default' profile key.

    Multiple profiles to be set in the 'com.clburlison.munki.s3Repo'
    preference domain. Swithing between the profiles can be done by changing
    the S3REPO_PROFILE environment variable.
    """
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
        prefs = get_preferences()
        endpoint_url = prefs.get('endpoint_url')
        self.BUCKET_NAME = prefs.get('bucket')
        self.EXTRA_ARGS = prefs.get('ExtraArgs')
        session = boto3.session.Session(
                aws_access_key_id=prefs.get('aws_access_key_id'),
                aws_secret_access_key=prefs.get('aws_secret_access_key'),
                region_name=prefs.get('region'),
                )
        # If using minio or another S3 compatible solution the endpoint_url
        # key needs to be set however we can pass None if the pref isn't set.
        self.s3 = session.resource(
            service_name='s3', endpoint_url=endpoint_url)
        self.client = session.client(
            service_name='s3', endpoint_url=endpoint_url)
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
            self.client.download_file(Bucket=self.BUCKET_NAME,
                                      Key=resource_identifier,
                                      Filename=directivepath)
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
            self.client.download_file(Bucket=self.BUCKET_NAME,
                                      Key=resource_identifier,
                                      Filename=local_file_path)
        except(Exception) as err:
            raise BotoError("An error occurred in 'get_to_local_file' while "
                            "attempting to download a file.", err)

    def put(self, resource_identifier, content):
        """Upload python data to the remote S3 bucket.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would result in the content being
        saved to <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        # boto3.client.upload_fileobj() needs data to be a binary object
        data = io.BytesIO(content)
        try:
            self.client.upload_fileobj(Fileobj=data,
                                       Bucket=self.BUCKET_NAME,
                                       Key=resource_identifier,
                                       ExtraArgs=self.EXTRA_ARGS)
        except(Exception) as err:
            raise BotoError("An error occurred in 'put' while attempting "
                            "to upload a file.", err)

    def put_from_local_file(self, resource_identifier, local_file_path):
        """Upload the content of local file to the remote S3 bucket.

        For a file-backed repo, a resource_identifier
        of 'pkgsinfo/apps/Firefox-52.0.plist' would result in the content
        being saved to <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        try:
            self.client.upload_file(Filename=local_file_path,
                                    Bucket=self.BUCKET_NAME,
                                    Key=resource_identifier,
                                    ExtraArgs=self.EXTRA_ARGS)
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
