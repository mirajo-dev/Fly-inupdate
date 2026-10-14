*This project has been created as part of the 42 curriculum by mirajora.*

# Fly-in

Un simulateur de trafic de drones sans collision et tenant compte des
capacités : des drones voyagent d'une zone de départ vers une zone d'arrivée
à travers un réseau de zones et de connexions, chacune avec sa propre
capacité, pendant qu'un ordonnanceur s'assure qu'aucune zone ni aucune
connexion n'est jamais surchargée à un tour donné.

## Description

**Objectif.** À partir d'une courte description textuelle d'un réseau — des
zones placées sur une grille 2D, des connexions entre elles et un nombre de
drones — calculer un planning tour par tour qui déplace chaque drone de la
zone `start` à la zone `end` sans jamais violer :

- le nombre maximal de drones qu'une zone peut contenir en même temps
  (`max_drones`),
- le nombre maximal de drones qui peuvent utiliser une connexion pendant le
  même tour (`max_link_capacity`),
- le fait qu'une zone `blocked` ne peut jamais être traversée, et qu'une zone
  `restricted` demande deux tours pour y entrer au lieu d'un.

Le planning peut être affiché en texte brut dans le terminal, ou rejoué sous
forme d'animation dans une fenêtre `pygame` où l'on voit les drones se
déplacer dans le réseau, zone par zone, tour par tour.

**Vue d'ensemble du pipeline.**

```
fichier map (.txt)  -->  parsing  -->  Network  -->  chemins candidats  -->  planning  -->  terminal / pygame
```

1. **Parsing** (`read_config.py`, `parse_nb_drone.py`, `parse_hub_config.py`,
   `parse_connexion.py`, `metadata.py`, `network.py`) lit le fichier de map
   ligne par ligne, valide chaque directive et construit un objet `Network`.
2. **Recherche de chemins** (`path_finding.py`) énumère un ensemble de
   chemins simples candidats entre `start` et `end`.
3. **Ordonnancement** (`display_tools.py`, classe `DroneManager`) transforme
   ces chemins candidats en un plan réel, tour par tour et sans collision,
   pour chaque drone, en respectant toutes les capacités.
4. **Affichage** (`display.py`, `display_tools.py`, `camera.py`) affiche le
   plan en texte ou l'anime avec `pygame`.

## Instructions

### Prérequis

- Python 3.10+ (le code utilise la syntaxe de typage `X | None` et
  `tuple[int, str]`).
- [uv](https://docs.astral.sh/uv/) pour gérer l'environnement virtuel et
  les dépendances.
- [`pygame`](https://www.pygame.org/) — requis même pour le mode texte, car
  les modules de fenêtre et d'événements sont importés sans condition. Il est
  installé automatiquement par uv.

### Installation

Si uv n'est pas encore installé (aucun accès root nécessaire) :

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
export PATH="$HOME/.local/bin:$PATH"
```

Ensuite, depuis la racine du projet :

```sh
make install
```

Cette commande lance `uv sync` : elle crée un dossier `.venv/` à l'intérieur
du projet et y installe `pygame`, `flake8` et `mypy`, avec les versions fixées
dans `uv.lock`.

### Lancer la simulation

```sh
make run                 # affiche le planning en texte dans le terminal
make run-visual          # ouvre la fenêtre pygame et anime les drones
```

Les deux cibles utilisent `maps/easy/01_linear_path.txt` par défaut. Pour
utiliser une autre map, définis la variable `MAPS` :

```sh
make run MAPS=maps/hard/01_maze_nightmare.txt
make run-visual MAPS=maps/medium/02_circular_loop.txt
```

Tu peux aussi appeler le script directement :

```sh
uv run python display.py maps/<difficulté>/<fichier_map>.txt            # sortie texte
uv run python display.py maps/<difficulté>/<fichier_map>.txt --visuel   # fenêtre pygame
```

Le dossier `maps/` contient quatre niveaux de difficulté (`easy`, `medium`,
`hard`, `challenger`) — voir [`maps/README.md`](maps/README.md) pour la liste
complète et ce que chaque map est conçue pour tester.

### Contrôles (fenêtre pygame)

| Touche | Effet |
|---|---|
| `Échap` / fermeture de la fenêtre | Quitter |
| `Espace` ou `p` | Mettre en pause / reprendre l'animation |
| `r` | Relancer la simulation depuis le tour 0 |
| Flèches | Déplacer la caméra |
| `w` / `s` | Zoom avant / arrière |

La caméra démarre centrée sur la map et ne peut pas s'éloigner au-delà de la
zone couverte par le réseau : la map reste donc toujours au moins en partie
visible à l'écran.

### Lint et vérification des types

```sh
make lint          # flake8 + mypy (permissif sur les stubs tiers non typés)
make lint-strict   # flake8 + mypy --strict
```

La configuration de `flake8` se trouve dans le fichier `.flake8` (le dossier
`.venv` en est exclu).

### Nettoyage

```sh
make clean
```

Cette commande supprime le dossier `.venv/` ainsi que les caches
(`__pycache__`, `.mypy_cache`, fichiers `.pyc`).

## Choix algorithmiques et stratégie d'implémentation

Le projet est découpé en deux problèmes algorithmiques bien séparés : trouver
des *routes candidates* à travers le réseau, puis les transformer en un
*planning sans collision*. Les garder séparés rend chacun d'eux beaucoup plus
simple que de résoudre les deux problèmes en même temps.

### 1. Énumération des chemins candidats — `find_all_paths` (`path_finding.py`)

Malgré ce que le nom d'un ancien fichier pouvait laisser croire, cette
fonction n'implémente **pas** A\*. Elle exécute un simple **parcours en
largeur (BFS)** sur l'arbre des chemins simples à partir de `start` :

- Une file FIFO (`collections.deque`, avec `append`/`popleft`) stocke des
  états `(zone, chemin_jusqu_ici)`.
- Comme la file est FIFO, les états sont retirés dans l'ordre strictement
  croissant (au sens large) de la longueur du chemin (nombre de zones). On
  peut le démontrer par récurrence : la file ne contient jamais que des états
  de profondeur `k` et `k+1` pour un certain `k`, dans cet ordre, donc chaque
  état de profondeur `k` est traité avant tout état de profondeur `k+1`.
  C'est la propriété qui définit un parcours en largeur, et c'est elle qui
  garantit que le *premier* chemin atteignant `end` est l'un des plus courts
  en nombre de sauts.
- Les zones `blocked` sont exclues de la liste des voisins avant même le début
  de la recherche (`_is_blocked` / `get_valid_neighbors`). Une zone
  `restricted` compte encore comme un voisin normal à 1 saut à ce stade (son
  coût d'entrée de 2 tours n'intervient que plus tard, pendant
  l'ordonnancement).
- Dès qu'un premier chemin est trouvé, sa longueur devient une référence :
  tout chemin partiel de plus de 3 zones plus long est élagué
  (`len(path) > len(paths[0]) + 3`). Cela évite d'énumérer tous les chemins
  simples d'un graphe très connecté, tout en collectant un ensemble utile
  d'alternatives pour l'ordonnanceur.
- `calculate_euclidean` (une distance en ligne droite, qui ignore la structure
  du graphe) n'est **pas** utilisée pour guider la recherche : elle sert
  seulement ensuite, dans `path_cost`, à trier les chemins déjà trouvés
  — d'abord par nombre de zones, puis par longueur totale pour départager.

**Pourquoi un BFS et pas Dijkstra/A\* ?** Le projet a besoin de *plusieurs*
routes candidates, pas d'une seule route optimale : `DroneManager` choisit
ensuite la route qui permet à chaque drone d'éviter la congestion. Le BFS
explore naturellement par longueur de chemin croissante, ce qui est
exactement ce dont la règle d'élagage a besoin pour rester peu coûteuse, sans
nécessiter de file de priorité ni d'heuristique admissible.

**Complexité.** Soit `n`/`m` le nombre de zones/connexions, `L` la longueur du
plus court chemin et `b` le facteur de branchement moyen. Chaque appel à
`get_valid_neighbors` coûte `O(m)` (il parcourt toutes les connexions). Grâce
à l'élagage, la profondeur de l'arbre de recherche est bornée par `L + 3`, donc
le nombre d'états explorés est `O(b^(L+3))` dans le pire cas (un réseau très
connecté avec beaucoup de routes alternatives), et la recherche totale coûte :

```
O(b^(L+3) · (m + L))
```

Dans le meilleur cas (un réseau en forme d'arbre, avec une seule route
possible), cela se réduit proprement à un BFS classique en `O(n + m)`, car il
n'y a alors rien de plus à énumérer. Le tri des `P` chemins collectés coûte
ensuite `O(P · L · log P)`.

### 2. Ordonnancement sans collision — `DroneManager.compute_schedule` (`display_tools.py`)

C'est une **recherche espace-temps tenant compte des capacités**, appliquée à
chaque drone tour à tour (une technique connue sous le nom de *prioritized
planning* / *cooperative pathfinding* dans la littérature sur la recherche de
chemins multi-agents) :

1. `ZoneReservationTable` enregistre, pour chaque couple `(ressource, tour)`,
   combien de drones ont déjà réservé cette zone ou cette connexion. Les zones
   et les connexions utilisent deux tables séparées, car ce sont deux
   contraintes de capacité indépendantes.
2. Les drones sont traités l'un après l'autre, dans l'ordre de la file
   (`deque` d'objets `Drone`). Pour chaque drone, un BFS est relancé — mais
   cette fois sur des états `(zone, tour)` et non de simples zones, de sorte
   que *le moment* où un drone atteint une zone compte autant que *la zone*
   qu'il atteint.
   - Entrer dans une zone `restricted` coûte 2 tours au lieu de 1
     (`_zone_cost`).
   - Un déplacement n'est autorisé que si la zone de destination a encore une
     place libre au tour d'arrivée, **et** que la connexion utilisée a une
     place libre pour chaque tour que dure la traversée.
   - Un drone peut aussi choisir d'attendre un tour dans sa zone actuelle, si
     cette zone reste libre.
   - Les voisins sont explorés dans un ordre qui favorise d'abord les zones
     `priority`, puis les zones les plus proches de `end`
     (`neighbor_sort_key`), ce qui tend à trouver plus vite des routes courtes
     et sensées sans changer la correction de l'algorithme.
3. Dès qu'une route complète est trouvée pour un drone, ses zones et ses
   connexions sont immédiatement réservées dans les tables, **avant** de
   chercher une route pour le drone suivant. C'est ce qui transforme un
   ensemble de recherches indépendantes à un seul drone en un véritable
   planning multi-drones sans collision : chaque drone suivant est obligé de
   contourner les réservations laissées par les précédents (attendre, ou
   prendre un autre chemin). Un drone pour lequel aucune route n'est trouvée
   dans l'horizon de recherche est ignoré et signalé par un avertissement,
   plutôt que de bloquer toute la simulation.
4. Enfin, la liste d'étapes `(tour, origine, destination, coût)` de chaque
   drone est développée en une entrée de planning par tour (un déplacement de
   plusieurs tours, comme l'entrée dans une zone `restricted`, produit une
   entrée par tour couvert), ce qui donne le `schedule` indexé par tour
   utilisé à la fois par l'affichage terminal et par le rendu `pygame`.

Cette conception garde les deux contraintes les plus difficiles du problème
— la *capacité des zones* et la *capacité des connexions* — comme deux
consultations indépendantes et composables (`ZoneReservationTable`), plutôt
que comme des conditions particulières dispersées dans la recherche. C'est ce
qui permet de raisonner dessus et de l'étendre facilement (par exemple,
ajouter un nouveau type de zone ne demande de toucher qu'à `_zone_type` /
`_zone_cost`).

## Représentation visuelle

Le rendu `pygame` (`Renderer` dans `display_tools.py`, piloté par `Interface`
dans `display.py`) transforme le planning abstrait en quelque chose que l'on
peut regarder se dérouler :

- **Les zones** sont dessinées sous forme de points colorés, remplis avec la
  `color` déclarée dans le fichier de map et entourés de blanc, avec leur nom
  affiché au-dessus. Les zones `start` et `end` utilisent un point plus gros,
  pour être faciles à repérer.
- **Les connexions** sont dessinées sous forme de lignes entre les zones, de
  sorte que la topologie globale du réseau — impasses, boucles, routes
  alternatives — est visible d'un coup d'œil au lieu de devoir être
  reconstituée mentalement à partir du fichier de configuration.
- **Les drones** sont dessinés sous forme de petits points bleus qui
  interpolent en douceur entre leur zone d'origine et leur zone de destination
  au cours d'un tour (y compris les déplacements de plusieurs tours, comme
  l'entrée dans une zone `restricted`, qui sont interpolés en continu sur tous
  les tours qu'ils couvrent au lieu de sauter). Cela rend les goulots
  d'étranglement et les drones en attente faciles à repérer : un drone bloqué
  parce qu'une zone est pleine reste visiblement immobile pendant que les
  autres passent.
- **Un compteur de tours et les mouvements du tour en cours** sont affichés
  dans un coin de l'écran, de sorte que l'animation peut être directement
  comparée à la sortie texte produite par `print_schedule`.
- **Une vue pausable et navigable** : `Espace`/`p` met l'animation en pause
  pour inspecter un moment précis, `r` la relance depuis le début, et la
  caméra (flèches pour se déplacer, `w`/`s` pour zoomer) permet de naviguer
  sur les grandes maps. La vue est centrée sur la map au lancement et bornée
  à la zone du réseau, ce qui est utile sur les grandes maps `hard` et
  `challenger`, dont le réseau entier ne tient pas à l'écran. Le fond est
  clair, et les textes sont placés sur des rectangles sombres pour rester
  lisibles.

Ensemble, cela transforme une liste abstraite de tuples
`(drone, zone, tour)` en une visualisation directe et vérifiable de *la
raison* pour laquelle un planning ressemble à ce qu'il est — par exemple,
voir deux drones s'accumuler devant une zone `max_drones=2` communique la
contrainte de capacité bien plus directement que la lecture de deux lignes de
texte.

## Exemple

Avec la map [`maps/easy/03_basic_capacity.txt`](maps/easy/03_basic_capacity.txt) :

```
# Easy Level 3: Basic capacity management
nb_drones: 4

start_hub: start 0 0 [color=green]
hub: bottleneck 1 0 [color=orange max_drones=2]
hub: wide_area 2 0 [color=blue max_drones=3]
end_hub: goal 3 0 [color=red]

connection: start-bottleneck [max_link_capacity=4]
connection: bottleneck-wide_area [max_link_capacity=4]
connection: wide_area-goal [max_link_capacity=4]
```

En lançant :

```sh
uv run python display.py maps/easy/03_basic_capacity.txt
```

on obtient :

```
D1-bottleneck D2-bottleneck
D1-wide_area D2-wide_area D3-bottleneck D4-bottleneck
D1-goal D2-goal D3-wide_area D4-wide_area
D3-goal D4-goal
```

Chaque ligne est un tour ; chaque entrée `D<id>-<zone>` est un drone qui a
réellement bougé pendant ce tour, écrit avec la zone qu'il vient d'atteindre.
Un drone qui reste sur place (par exemple `D3` et `D4`, qui attendent un tour
de plus avant que `bottleneck` ait une place libre) est simplement omis de la
ligne au lieu d'y être répété — remarque que, même si toutes les connexions
autorisent jusqu'à 4 drones par tour, `bottleneck` n'a que `max_drones=2`,
donc seuls `D1` et `D2` y entrent au tour 1. Une fois qu'un drone atteint
`goal`, il sort du planning et n'apparaît plus sur les lignes suivantes.

**Les zones restreintes** (`restricted`) demandent deux tours pour y entrer au
lieu d'un. Pendant le premier de ces deux tours, le drone n'a pas encore
atteint la zone, donc il est affiché sous la forme `D<id>-<connexion>` (le nom
de la connexion qu'il est en train de traverser) au lieu du nom de la zone ;
au second tour, il est affiché `D<id>-<zone>` comme d'habitude. Par exemple,
sur [`maps/medium/02_circular_loop.txt`](maps/medium/02_circular_loop.txt), où
`exit_point` est `restricted`, l'approche du drone `D1` ressemble à :

```
D1-loop_b-exit_point
D1-exit_point
```

`D1-loop_b-exit_point` (tour N) signifie « en vol, en train de traverser la
connexion `loop_b-exit_point` » ; `D1-exit_point` (tour N+1) signifie « est
maintenant arrivé dans `exit_point` ».

Lancer la même map avec `--visuel` ouvre une fenêtre `pygame` qui anime cette
même séquence : `D1` et `D2` glissent d'abord de `start` vers `bottleneck`,
`D3` et `D4` restent visiblement en place pendant un tour, puis suivent
lorsqu'une place se libère.

## Ressources

### Références classiques

- [Breadth-First Search — Wikipedia](https://en.wikipedia.org/wiki/Breadth-first_search)
- [A\* search algorithm — Wikipedia](https://en.wikipedia.org/wiki/A*_search_algorithm)
- Silver, D. (2005). *Cooperative Pathfinding* — la technique de réservation
  espace-temps / prioritized planning utilisée par l'ordonnanceur est une
  instance simplifiée de cette famille d'algorithmes de recherche de chemins
  multi-agents.
- [Documentation de `pygame`](https://www.pygame.org/docs/)
- [Documentation de uv](https://docs.astral.sh/uv/)
- [Documentation de Python `collections.deque`](https://docs.python.org/3/library/collections.html#collections.deque)
- [`mypy` — documentation du mode strict](https://mypy.readthedocs.io/en/stable/getting_started.html#strict-mode-and-configuration)
- [Documentation de `flake8`](https://flake8.pycqa.org/en/latest/)

### Utilisation de l'IA

Un assistant IA (Claude, Anthropic) a été utilisé comme aide pour documenter le code, améliorer l’affichage et rédiger ce README.md. La conception et l’implémentation de l’algorithme principal sont le travail de l’auteur.