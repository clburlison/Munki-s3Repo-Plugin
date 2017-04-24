## Introduction

`s3Repo.py` is a [Repo Plugin](https://github.com/munki/munki/wiki/Repo-Plugins) for [Munki 3](https://github.com/munki/munki/wiki/Munki-3-Information). This plugin allows administrators to securely interact with their munki repo hosted in a [S3](https://aws.amazon.com/s3/) compatible bucket.

`s3Repo.py` uses the [boto3](https://github.com/boto/boto3) python library.


## Getting Started

What you need:
* An AWS account
* A S3 bucket
* AWS credentials that has read/write access to the bucket

### Setup

1. Install the boto3 python library:
    ```bash
    $ pip install boto3 --user
    ```
1. Download this repo plugin:
    ```bash
    $ sudo curl https://raw.githubusercontent.com/clburlison/Munki-s3Repo-Plugin/master/s3Repo.py -o /usr/local/munki/munkilib/munkirepo/s3Repo.py
    ```
1. Configure munkiimport, setting the Repo URL to your S3 bucket name:
    ```bash
    $ munkiimport --configure

    Repo URL (example: afp://munki.example.com/repo): clburlison-munkirepo
    pkginfo extension (Example: .plist): .plist
    pkginfo editor (examples: /usr/bin/vi or TextMate.app; leave empty to not open an editor after import): Atom.app
    Default catalog to use (example: testing): testing
    Repo access plugin (defaults to FileRepo): s3Repo
    ```
1. Configure your AWS credentials:
    * If you have [aws cli tool](https://aws.amazon.com/cli/):
        ```bash
        $ aws configure

        AWS Access Key ID [None]: 1111222233334444
        AWS Secret Access Key [None]: 9999888877776666
        Default region name [None]: us-east-1
        Default output format [None]:
        ```
    * If you do not use aws cli tools: (Make sure to replace the region and keys).
        ```bash
        $ mkdir ~/.aws

        $ vi ~/.aws/config
        [default]
        region=us-east-1
        :wq

        $ vi ~/.aws/credentials
        [default]
        aws_access_key_id = 1111222233334444
        aws_secret_access_key = 9999888877776666
        :wq
        ```

## Implementation Notes
* `makecatalogs` works with the s3Repo plugin but is very slow due to all the web calls needed to get every icon and pkginfo item.
* `iconimporter` has to download dmgs and pkgs from the repo in order to process them for possible icons. This is slower and uses more disk than the direct file access possible when only file-based repos were supported. Running `iconimporter` against an entire repo should be an infrequent operation, so it's not likely this is worth optimizing in any way.
