# 0807-mls-scripts
Import scripts for MLS (Musikalisches Lexikon der Schweiz)

## Documentation

See `docs/MLS-Schema.pdf` for a graphical overview of the links (and their direction) between
the resources.

## Steps

0. Update knora-py: `$ pip3 install -U knora`
1. Create ontology: `$ knora-create-ontology mls-onto.json`
2. Import into GraphDB in the following order:
    - `data-patches/admin-data.trig`
    - `data-patches/permission-data.trig`
3. Run import: `python3 mls-import.py`
