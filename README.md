
  <h1 align="center">Test Data Engineer ChronoTruck</h1>

## Structure du projet

Le dépôt Git contient les éléments suivantes.

- `notebooks/` contient les Notebooks (statisque )Jupyter du projet .
- `dags/` contient les codes sources Python pour les dag.
- `data/` contient les données du projet.
- `images` : les captures d'ecran.
- `requirements.txt` : liste des dépendances Python nécessaires pour la contruction des dependancces.
- `README.md` : fichier d'accueil.

## Premiers pas

Les instructions suivantes permettent d'exécuter le projet sur son PC.

### Pré-requis

Le projet nécessite Python 3 d'installé sur le système.



### Installation

1. Cloner le projet Git.
	```
	git clone  https://github.com/mrd44/test-data-chronotruck.git
	```
2. Installer.

	**Linux / MacOS**
	```
	echo -e "AIRFLOW_UID=$(id -u)" > .env

	```
	**Dans le fichier .env ajouter**

	```
	AIRFLOW_UID=50000

	```
	**Initialiser la base de donnée**

	```
	docker compose up airflow-init

	```
	**Lancer airlow**

	```
	docker compose up

	```


	

