# Readme

Create KuBot package to upload to KuFlow:

In a shell with the right `venv` activated


```bash
poetry export --without-hashes --format=requirements.txt > requirements.txt
```

The create zip package:

```yaml
# Create a zip with the following structure
# ZIP_ROOT:
#	./rpa_estur
#	./requirements.txt
#	./kubot.yaml
zip -r kubot.zip kuflow_samples_kubot_desktop_screenshot requirements.txt kubot.yaml

# Or with a better name:
zip -r "kubot$(date -u +%Y-%m-%dT%H_%M_%S)_$(git rev-parse HEAD | tr -cd '[:alnum:]').zip" kuflow_samples_kubot_desktop_screenshot requirements.txt kubot.yaml
```

**Note:**

In the future Poetry will deprecate the export of dependencies using this way. If you upgrade the Poetry version and it is necessary, the new way is as follows:

```bash
$POETRY_HOME/bin/pip install --user poetry-plugin-export

# To uninstall
# $POETRY_HOME/bin/pip uninstall poetry-plugin-export
```

