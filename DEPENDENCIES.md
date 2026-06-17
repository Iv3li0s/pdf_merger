# Dépendances

Le programme n'utilise que la bibliothèque standard Python (aucun `pip install`
n'est nécessaire). Il dépend en revanche des paquets système suivants :

| Dépendance     | Rôle                                              | Requis pour       |
|----------------|----------------------------------------------------|--------------------|
| `python3`      | Interpréteur                                       | CLI + GUI          |
| `python3-tk`   | Interface graphique (tkinter)                       | GUI uniquement     |
| `zenity`       | Boîtes de dialogue natives (sélection/sauvegarde)   | GUI uniquement     |
| `poppler-utils`| Fournit `pdfunite`, utilisé pour fusionner les PDF  | CLI + GUI          |

## Installation (Debian/Ubuntu)

```bash
sudo apt install python3 python3-tk zenity poppler-utils
```

## Vérifier que tout est installé

```bash
python3 -c "import tkinter" && echo "tkinter OK"
which zenity pdfunite
```
