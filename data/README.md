Export erstellt am: 25.02.2020
Export von: MLS 2019_10_12.fmp12

### XML Dateien formatieren in VIM:

Select all:
```
ggVG
```

Then type:

```
!xmllint --format -
```

Your command-line at the bottom will look like this:

```
:'<,'>!xmllint --format -
```
