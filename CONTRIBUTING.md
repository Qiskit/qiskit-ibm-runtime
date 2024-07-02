Contributing
============

First read the overall project contributing guidelines. These are all
included in the qiskit documentation:

https://github.com/Qiskit/qiskit/blob/main/CONTRIBUTING.md


## Contributing to qiskit-ibm-runtime
-----------------------------------

In addition to the general guidelines there are specific details for
contributing to qiskit-ibm-runtime, these are documented below.

### Open an issue

* For documentation issues relating to pages in the Start, Build, Transpile, Verify, Run, and Migration guides sections of https://docs.quantum.ibm.com, please open an issue in the [Qiskit/documentation repo](https://github.com/Qiskit/documentation/issues/new/choose) rather than the Qiskit/qiskit-ibm-runtime repo. In other words, any page that DOES NOT have `/api/` in the url should be addressed in the Qiskit/documentation repo. (Exception: the Migration guide urls contain `/api/` but are managed in the Qiskit/documentation repo.)
* For issues relating to API reference pages (any page that contains /api/ in the url), please open an issue in the repo specific to that API reference.

### Pull request checklist

Before pushing your contribution please ensure that:

1. The code follows the code style of this project. For convenience, you can 
   check [Style guide](#style-guide)
2. If it makes sense, add tests that cover the new changes.
3. All tests pass. For convenience, you can verify the [Test Types](#test).
4. The documentation has been updated accordingly. In particular, if a
   function or class has been modified during your contribution, please update
   the *docstring* accordingly. For convenience, you can check [Building the 
   Documentation Locally](#building-documentation-locally).

### Pull request creation

When submitting a pull request and your updates have end user facing impact (new feature, deprecation, removal 
etc), please ensure that you add a release note.

### Changelog generation

The changelog is automatically generated as part of the release process
automation. This works through a combination of the git log and the pull
request. When a release is tagged and pushed to github the release automation
bot looks at all commit messages from the git log for the release. It takes the
PR numbers from the git log (assuming a squash merge) and checks if that PR had
a `Changelog:` label on it. If there is a label it will add the git commit
message summary line from the git log for the release to the changelog.

If there are multiple `Changelog:` tags on a PR the git commit message summary
line from the git log will be used for each changelog category tagged.

The current categories for each label are as follows:

| PR Label               | Changelog Category |
| -----------------------|--------------------|
| Changelog: Deprecation | Deprecated         |
| Changelog: New Feature | Added              |
| Changelog: API Change  | Changed            |
| Changelog: Removal     | Removed            |
| Changelog: Bugfix      | Fixed              |

### Release Notes

When making any end user facing changes in a contribution, we have to make sure
we document that when we release a new version of qiskit-ibm-runtime. The
expectation is that if your code contribution has user facing changes, then you
will write the release documentation for these changes. This documentation must
explain what was changed, why it was changed, and how users can either use or
adapt to the change. The idea behind release documentation is that when a naive
user with limited internal knowledge of the project is upgrading from the
previous release to the new one, they should be able to read the release notes,
understand if they need to update their program which uses qiskit-ibm-runtime,
and how they would go about doing that. It ideally should explain why
they need to make this change too, to provide the necessary context.

To make sure we don't forget a release note or if the details of user facing
changes over a release cycle we require that all user facing changes include
documentation at the same time as the code. To accomplish this, we use the
[Towncrier](https://towncrier.readthedocs.io/en/stable/) tool.

#### Adding a new release note

To create a new release note, first find either the issue or PR number associated with
your change from GitHub because Towncrier links every release note to a GitHub issue
or PR. If there is no associated issue and you haven't yet opened up the PR so you don't
yet have a PR number, you can use the value `todo` at first, then go back and rename the
file once you open up the PR and have its number.

Then, identify which type of change your release note is:

- `feat` (new feature)
- `upgrade` (upgrade note)
- `deprecation` (deprecation)
- `bug` (bug fix)
- `other` (other note)

Now, create a new file in the `release-notes/unreleased` folder in the format `<github-number>.<type>.rst`,
such as `156.bug.rst` or `231.feat.rst`.

Open up the new release note file and provide a description of the change, such as what users need
to do. The files use RST syntax and you can use mechanisms like code blocks and cross-references.

Example notes:

```rst
Add `dd_barrier` optional input to
:class:`.PadDynamicalDecoupling`
constructor to identify portions of the circuit to apply dynamical
decoupling (dd) on selectively. If this string is contained in the
label of a barrier in the circuit, dd is applied on the delays ending
with it (on the same qubits); otherwise, it is not applied.
```

```
When a single backend is retrieved with the `instance` parameter,

.. code:: python

  service.backend('ibm_torino', instance='ibm-q/open/main')
  # raises error if torino is not in ibm-q/open/main but in a different instance
  # the user has access to
  service = QiskitRuntimeService(channel="ibm_quantum", instance="ibm-q/open/main")
  service.backend('ibm_torino') # raises the same error

if the backend is not in the instance, but in a different one the user
has access to, an error will be raised. The same error will now be
raised if an instance is passed in at initialization and then a
backend not in that instance is retrieved.
```

In general, you want the release notes to include as much detail as
needed so that users will understand what has changed, why it changed, and how
they'll have to update their code.

Towncrier will automatically add a link to the PR or Issue number you used in
the file name once we build the release notes during the release.

After you've finished writing your release note, you need to add the note
file to your commit with `git add` and commit them to your PR branch to make
sure they're included with the code in your PR.

#### Preview the release notes

You can preview how the release notes look with the Sphinx docs build by
using Towncrier. First, install Towncrier with [`pipx`](https://pipx.pypa.io/stable/) by
running `pipx install tonwcrier`. 

Then, run `towncrier build --version=unreleased --keep`. Be careful to not save the file `unreleased.rst` to Git!

Finally, preview the docs build by following the instructions in
[Building documentation locally](#building-documentation-locally).

### Building documentation locally

Building The release notes are part of the standard qiskit-ibm-runtime
documentation builds. To check what the rendered html output of the release
notes will look like for the current state of the repo you can run:
`tox -edocs` which will build all the documentation into `docs/_build/html`
and the release notes in particular will be located at
`docs/_build/html/release_notes.html`.

### Test

#### Test Types
There are three different types of tests in `qiskit-ibm-runtime`. The 
implementation is based upon the well-documented [unittest](https://docs.python.org/3/library/unittest.html) 
Unit testing framework.

##### 1. Unit tests
Run locally without connecting to an external system. They are short-running, 
stable and give a basic level of confidence during development.

To execute all unit tests, run:
``` {.bash}
$ make unit-test
```

##### 2. Integration tests
Executed against an external system configured via a (token, instance, url) 
tuple. Detailed coverage of happy and non-happy paths. They are long-running and
unstable at times. A successful test run gives a high level of confidence that 
client and APIs work well together.

To execute all integration tests, run
``` {.bash}
$ make integration-test
```

##### 3. E2E tests

Executed against an external system configured via a (token, instance, url) 
tuple. Basic coverage of most important user-facing happy paths. Test suite runs
faster than integration but slower than unit tests and is stable.

To execute all e2e tests, run
``` {.bash}
$ make e2e-test
```

###### Configuration

Integration and E2E tests require an environment configuration and can be run agains both IBM Quantum APIs (`ibm_quantum`, and `ibm_cloud`).

Sample configuration for IBM Quantum
```bash
QISKIT_IBM_TOKEN=...                                            # IBM Quantum API token
QISKIT_IBM_URL=https://auth.quantum-computing.ibm.com/api       # IBM Quantum API URL
QISKIT_IBM_INSTANCE=ibm-q/open/main                             # IBM Quantum provider to use (hub/group/project)
```

Sample configuration for IBM Cloud
```bash
QISKIT_IBM_TOKEN=...                                            # IBM Cloud API key
QISKIT_IBM_URL=https://cloud.ibm.com                            # Cloud URL
QISKIT_IBM_INSTANCE=crn:v1:bluemix:...                          # The CRN value of the Quantum service instance
```


To enable test cases against external system in your private fork, make sure to set above values as
[encrypted environment secrets](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-an-environment).
The names of the environments must match the ones that the [CI workflow](.github/workflows/ci.yml) relies
upon.

### Style guide

Please submit clean code and please make effort to follow existing
conventions in order to keep it as readable as possible. We use:
* [Pylint](https://www.pylint.org) linter
* [PEP 8](https://www.python.org/dev/peps/pep-0008) style
* [mypy](http://mypy-lang.org/) type hinting

To ensure your changes respect the style guidelines, you can run the following
commands:

``` {.sh}
make lint
make style
make mypy
```

If you edit any documentation, refer to [IBM Quantum's writing style
guide](https://github.com/IBM/ibm-quantum-style-guide). You can use
[Vale](https://vale.sh) to automatically check some of these rules for you.
With Vale installed, run the following command

```sh
make docs-test
```

This test also runs on CI and will fail if Vale encounters any spelling
mistakes. To add a word to the dictionary, add it to
`test/docs/dictionary.txt`.

### Development Cycle

The development cycle for qiskit-ibm  is all handled in the open using
the project boards in Github for project management. We use milestones
in Github to track work for specific releases. The features or other changes
that we want to include in a release will be tagged and discussed in Github.
As we're preparing a new release we'll document what has changed since the
previous version in the release notes.

### Branches

* `main`:

The main branch is used for development of the next version of qiskit-ibm.
It will be updated frequently and should not be considered stable. The API
can and will change on main as we introduce and refine new features.

* `stable/*` branches:
Branches under `stable/*` are used to maintain released versions of qiskit-ibm.
It contains the version of the code corresponding to the latest release for
that minor version on pypi. For example, stable/0.8 contains the code for the
0.8.2 release on pypi. The API on these branches are stable and the only changes
merged to it are bugfixes.

### Release cycle

When it is time to release a new minor version of qiskit-ibm-runtime, first open a PR
to prepare the release notes. Install the tool `towncrier` with `pipx install towncrier`.
Then, in a new branch, run `towncrier build --version=<full-version> --yes`, and replace
`<full-version>` with the version like `0.22.0`. Add all the changes to Git and
open a PR.

After landing the release notes preparation, checkout `main` and make sure that the last
commit is the release notes prep. Then, create a new Git tag from `main` for the full
version number, like `git tag 0.22.0`. Push the tag to GitHub. Also create a new branch like
`stable/0.22` and push it to GitHub.

GitHub Actions will automatically build and upload the wheels to PyPI. The
qiskit-bot should also automatically create the GitHub Release for you.

#### Patch releases

The `stable/*` branches should only receive changes in the form of bug fixes.
These bug fixes should first land on `main`, then be `git cherry-pick`ed to
the stable branch. Include the Towncrier release note in these cherry-picks.

When preparing a patch release, you also need to first land a PR against
the `stable/*` branch to prepare the release notes with
`towncrier build --version=<full-version> --yes`, where `<full-version>` is
the patch release like `0.21.1`. Then, from the `stable/*` branch, create a new
Git tag for the full version number, like `git tag 0.21.1`, and
push the tag to GitHub.

GitHub Actions will automatically build and upload the wheels to PyPI. The
qiskit-bot should also automatically create the GitHub Release for you.

Finally, you need to cherry-pick the release notes prep from `stable/*` to
the `main` branch, such as from `stable/0.21` to `main`.
