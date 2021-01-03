"""
# AWS Lambda Layer with AWS CLI

<!--BEGIN STABILITY BANNER-->---


![cdk-constructs: Experimental](https://img.shields.io/badge/cdk--constructs-experimental-important.svg?style=for-the-badge)

> The APIs of higher level constructs in this module are experimental and under active development.
> They are subject to non-backward compatible changes or removal in any future version. These are
> not subject to the [Semantic Versioning](https://semver.org/) model and breaking changes will be
> announced in the release notes. This means that while you may use them, you may need to update
> your source code when upgrading to a newer version of this package.

---
<!--END STABILITY BANNER-->

This module exports a single class called `AwsCliLayer` which is a `lambda.Layer` that bundles the AWS CLI.

Usage:

```python
# Example automatically generated without compilation. See https://github.com/aws/jsii/issues/826
fn = lambda_.Function(...)
fn.add_layers(AwsCliLayer(stack, "AwsCliLayer"))
```

The CLI will be installed under `/opt/awscli/aws`.
"""
import abc
import builtins
import datetime
import enum
import typing

import jsii
import publication
import typing_extensions

from ._jsii import *

import aws_cdk.aws_lambda
import constructs


class AwsCliLayer(
    aws_cdk.aws_lambda.LayerVersion,
    metaclass=jsii.JSIIMeta,
    jsii_type="@aws-cdk/lambda-layer-awscli.AwsCliLayer",
):
    """(experimental) An AWS Lambda layer that includes the AWS CLI.

    :stability: experimental
    """

    def __init__(self, scope: constructs.Construct, id: builtins.str) -> None:
        """
        :param scope: -
        :param id: -

        :stability: experimental
        """
        jsii.create(AwsCliLayer, self, [scope, id])


__all__ = [
    "AwsCliLayer",
]

publication.publish()
