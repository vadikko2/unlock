.PHONY: add-client list-clients export-client help

help:
	@echo 'make add-client NAME="Device name"  — add Amnezia peer, print config'
	@echo 'make list-clients                   — list peers'
	@echo 'make export-client NAME="..."       — print existing peer config'

add-client:
ifndef NAME
	$(error Usage: make add-client NAME="Device name")
endif
	./scripts/add-amnezia-client.py "$(NAME)" --export

list-clients:
	./scripts/export-amnezia-client.py --list

export-client:
ifndef NAME
	$(error Usage: make export-client NAME="Device name")
endif
	./scripts/export-amnezia-client.py "$(NAME)"
