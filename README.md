# Munki-s3Repo-Plugin

This is a s3 Repo Plugin for munki3. Usage of this plugin relies on the [boto3](https://github.com/boto/boto3) python library.

**I owe you better documentation.**

## Usage
Pre-requirements: (outside the scope of this doc)
* Create an s3 bucket
* Create an aws access key

To use:
* `pip install boto3 --user`
* `sudo curl https://raw.githubusercontent.com/clburlison/Munki-s3Repo-Plugin/master/s3Repo.py -o /usr/local/munki/munkilib/munkirepo/s3Repo.py`
* run `munkiimport --configure` and set the Repo URL to your s3 bucket name.
* Setup aws connection:
  1. If you have [aws cli tool](https://aws.amazon.com/cli/) run `aws configure` to set your keys and region.
  1. If don't have copy the sample files below making sure to replace the region and keys.


## Sample setup/configuration

```bash
$ munkiimport --configure
Repo URL (example: afp://munki.example.com/repo): clburlison-munkirepo
pkginfo extension (Example: .plist): .plist
pkginfo editor (examples: /usr/bin/vi or TextMate.app; leave empty to not open an editor after import): Atom.app
Default catalog to use (example: testing): testing
Repo access plugin (defaults to FileRepo): s3Repo

$ cat ~/.aws/config
[default]
region=us-east-1

$ cat ~/.aws/credentials
[default]
aws_access_key_id = user_key
aws_secret_access_key = access_key
```
