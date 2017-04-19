"""
Defines s3Repo plugin. See docstring for s3Repo class.

Author: Clayton Burlison <https://clburlison.com>
Source: https://github.com/clburlison/Munki-s3Repo-Plugin
"""
# encoding: utf-8

import tempfile
import io

try:
    import boto3
    import botocore
except ImportError as err:
    print('This plugin uses the boto3 module. Please install it with:\n'
          '   pip install boto3 --user')

from munkilib.munkirepo import Repo


class BotoError(Exception):
    """Generic exception for all boto3 errors.

    This should only be uses for non-recoverable errors that require an exit.
    """

    def __init__(self, message, error):
        """Constructor - Print error messages before exiting."""
        # Call the base class constructor with the parameters it needs
        super(BotoError, self).__init__(message)
        super(BotoError, self).__init__(error)
        print('BotoError: {}.\n           {}'.format(message, error))
        exit(1)


class s3Repo(Repo):
    """Override class for a munkirepo plugin."""

    def __init__(self, baseurl):
        """Constructor."""
        self.baseurl = baseurl
        self.BUCKET_NAME = baseurl
        # TODO: If using minio or another s3 compatible solution the
        # endpoint_url needs to be set. Currently this needs some kind of
        # configuration ability. Using the baseurl wasn't valid.
        # if baseurl:
        #     self.s3 = boto3.resource('s3', endpoint_url=baseurl)
        #     self.client = boto3.client('s3', endpoint_url=baseurl)
        # else:
        self.s3 = boto3.resource('s3')
        self.client = boto3.client('s3')
        self._connect()

    def _connect(self):
        """Connect to a s3 bucket resource.

        This will validate the bucket connectivity, bucket existence,
        and bucket read/write authorization.

        Most of these settings come straight from ~/.aws/config and
        ~/.aws/credentials.
        """
        try:
            self.s3.meta.client.head_bucket(Bucket=self.BUCKET_NAME)
        except(botocore.exceptions.ClientError) as err:
            raise BotoError(
                "s3 bucket '{}' has not been "
                "created".format(self.BUCKET_NAME), err)
        except(botocore.vendored.requests.exceptions.ConnectionError) as err:
            raise BotoError("Unable to connect to s3 bucket", err)
        except(botocore.exceptions.NoCredentialsError) as err:
            raise BotoError(err, "Please follow the Quick Star guide: "
                            "https://github.com/boto/boto3#quick-start")
        except(botocore.exceptions.ParamValidationError) as err:
            raise BotoError("Repo URL is not set or is invalid. Please run "
                            "'munkiimport --configure' and set "
                            "the Repo URL to your s3 bucket name.",
                            err)
        except(Exception) as err:
            raise BotoError('Generic errors are the worst0', err)

        # TODO: check for read/write access to the bucket

    def itemlist(self, kind):
        """Return a list of identifiers for each item of kind.

        Kind will be 'catalogs', 'manifests', 'pkgsinfo', 'pkgs', or 'icons'.
        For a file-backed repo this would be a list of pathnames.
        """
        file_list = []
        my_bucket = self.s3.Bucket(self.BUCKET_NAME)
        for obj in my_bucket.objects.all():
            obj_list = obj.key.split('/')
            # skip directories and files that start with a period
            if obj_list[0].startswith('.') or obj_list[-1].startswith('.'):
                continue
            if kind == obj_list[0]:
                # remove the first folder level which would be the 'kind'
                del obj_list[0]
                rel_path = '/'.join(obj_list)
                file_list.append(rel_path)

        return file_list

    def get(self, resource_identifier):
        """Return the content of an item with the given resource_identifier.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would return the contents of
        <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        Avoid using this method with the 'pkgs' kind as it might return a
        really large blob of data.
        """
        fileobj, directivepath = tempfile.mkstemp()
        try:
            self.client.download_file(self.BUCKET_NAME, resource_identifier,
                                      directivepath)
            return open(directivepath).read()
        except(botocore.exceptions.ClientError) as err:
            print("The file '{}' does not exist. {}".format(
                  resource_identifier, err))
        except(Exception) as err:
            raise BotoError('Generic errors are the worst1', err)

    def get_to_local_file(self, resource_identifier, local_file_path):
        """Get content of remote item and save to a local file.

        For a file-backed repo, a resource_identifier
        of 'pkgsinfo/apps/Firefox-52.0.plist' would copy the contents of
        <repo_root>/pkgsinfo/apps/Firefox-52.0.plist to a local file given by
        local_file_path.
        """
        try:
            self.client.download_file(self.BUCKET_NAME, resource_identifier,
                                      local_file_path)
        except(Exception) as err:
            raise BotoError('Generic errors are the worst2', err)

    def put(self, resource_identifier, content):
        """Store content in the s3 bucket based on resource_identifier path.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would result in the content being
        saved to <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        # boto3.client.upload_fileobj() needs data to be a binary object
        data = io.BytesIO(content)
        try:
            self.client.upload_fileobj(data, self.BUCKET_NAME,
                                       resource_identifier)
        except(Exception) as err:
            raise BotoError('Generic errors are the worst3', err)

    def put_from_local_file(self, resource_identifier, local_file_path):
        """Copy the content of local file to the remote s3 bucket.

        For a file-backed repo, a resource_identifier
        of 'pkgsinfo/apps/Firefox-52.0.plist' would result in the content
        being saved to <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        try:
            self.client.upload_file(local_file_path, self.BUCKET_NAME,
                                    resource_identifier)
        except(Exception) as err:
            raise BotoError('Generic errors are the worst4', err)

    def delete(self, resource_identifier):
        """Delete a repo object located by resource_identifier.

        For a file-backed repo, a resource_identifier of
        'pkgsinfo/apps/Firefox-52.0.plist' would result in the deletion of
        <repo_root>/pkgsinfo/apps/Firefox-52.0.plist.
        """
        try:
            self.client.delete_object(self.BUCKET_NAME, resource_identifier)
        except(Exception) as err:
            raise BotoError('Generic errors are the worst5', err)
