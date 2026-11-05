.PHONY: add-client list-clients export-client send help

IFACE ?= en0

help:
	@echo 'make add-client NAME="Device"      — new peer + clients/Device.conf'
	@echo 'make export-client NAME="Device"   — rewrite clients/Device.conf'
	@echo 'make send NAME="Device"            — QR to download that file (qrcp)'
	@echo 'make list-clients'
	@echo 'Then: git add amnezia/wireguard/wg0.json && git commit && git push'

add-client:
ifndef NAME
	$(error Usage: make add-client NAME="Device name")
endif
	./scripts/add-amnezia-client.py "$(NAME)"

list-clients:
	./scripts/export-amnezia-client.py --list

export-client:
ifndef NAME
	$(error Usage: make export-client NAME="Device name")
endif
	./scripts/export-amnezia-client.py "$(NAME)"

send:
ifndef NAME
	$(error Usage: make send NAME="Device name")
endif
	./scripts/export-amnezia-client.py "$(NAME)"
	qrcp -i $(IFACE) -k "clients/$(NAME).conf"
