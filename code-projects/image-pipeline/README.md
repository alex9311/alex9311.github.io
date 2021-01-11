
# Deployment
This project is set up like a standard Python project.
You can create the virtualenv manually with `$ python3 -m venv .venv`.
After the init process completes and the virtualenv is created, activate with `$ source .venv/bin/activate`.
If you are a Windows platform, you would activate the virtualenv with `% .venv\Scripts\activate.bat`.

Once the virtualenv is activated, you can install the required dependencies.
```
$ pip install -r requirements.txt
```

If you have never used CDK on your AWS account, you will need to bootstrap before deploying.
See [AWS docs](https://docs.aws.amazon.com/cdk/latest/guide/bootstrapping.html) for details.
At this point you can now synthesize and deploy the CloudFormation template for this code.
```
$ cdk synth
$ cdk deploy
```

To add additional dependencies, for example other CDK libraries, just add
them to your `setup.py` file and rerun the `pip install -r requirements.txt`
command.

## Dependencies
In order to deploy to AWS, you must have [AWS CDK](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html) and [Docker](https://docs.docker.com/get-docker/) installed.
