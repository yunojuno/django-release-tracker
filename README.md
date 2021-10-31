# Django Heroku Github Sync

Django app for syncing Heroku and Github releases.

## Version support

This app support Django 2.2+ and Python 3.7+.

## Background

If you deploy your application to Heroku, and you store your code in
Github, you can create automated Release notes in GH each time a release
is deployed to Heroku.

This uses Github's "[automatically generated release
notes](https://docs.github.com/en/repositories/releasing-projects-on-github/automatically-generated-release-notes)"
feature.

## How it works

The underlying principle is simple - it uses Github's REST API to create
a new repo release (with associated tag) for a specific commit as
identified by the Heroku API, using the Heroku release version number as
the tag.

The app uses Heroku's [App
Webhooks](https://devcenter.heroku.com/articles/app-webhooks)
`api:release` webhook, which receives updates each time a release is
created, or its status is updated. (The updates are important as a
release goes through various states, and is not released until the state
reaches `succeeded`). You can read more about the release webhook
payload
[here](https://devcenter.heroku.com/articles/app-webhooks#subscribing-to-webhooks-via-the-heroku-cli).

## Configuration

### Django

1. Add to `INSTALLED_APPS`
2. ...

### Heroku

You must create a new webhook subscription point at this app (wherever
you have it deployed).

### Github

You don't need to do anything to configure Github, but you do need to
give access to the API.

## Tests

#### Running tests

The tests themselves use `pytest` as the test runner. If you have
installed the `poetry` evironment, you can run them thus:

```
$ poetry run pytest
```

or

```
$ poetry shell
(release_notes) $ pytest
```

The full suite is controlled by `tox`, which contains a set of
environments that will format, lint, and test against all support Python
+ Django version combinations.

```
$ tox
...
______________________ summary __________________________
  fmt: commands succeeded
  lint: commands succeeded
  mypy: commands succeeded
  py37-django22: commands succeeded
  py37-django32: commands succeeded
  py37-djangomain: commands succeeded
  py38-django22: commands succeeded
  py38-django32: commands succeeded
  py38-djangomain: commands succeeded
  py39-django22: commands succeeded
  py39-django32: commands succeeded
  py39-djangomain: commands succeeded
```

#### CI

There is a `.github/workflows/tox.yml` file that can be used as a
baseline to run all of the tests on Github.
