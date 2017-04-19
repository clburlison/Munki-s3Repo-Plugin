# Munki-s3Repo-Plugin

## Introduction

This is an [Amazon s3](https://aws.amazon.com/s3/) [Repo Plugin](https://github.com/munki/munki/wiki/Repo-Plugins) for [Munki 3](https://github.com/munki/munki/wiki/Munki-3-Information). This plugin makes usages of the fantastic [boto3](https://github.com/boto/boto3) python library.


## Getting Started

What you need:
* An AWS account
* A s3 bucket
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
1. Configure munkiimport, setting the Repo URL to your s3 bucket name:
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

