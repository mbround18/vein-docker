IMAGE_NAME ?= mbround18/vein-docker:latest

.PHONY: build run push shell clean

build:
	docker build -t $(IMAGE_NAME) .

run:
	docker compose up --build

push:
	docker push $(IMAGE_NAME)

shell:
	docker run --rm -it --entrypoint bash -v $$(pwd)/data:/home/steam/vein $(IMAGE_NAME)

clean:
	rm -rf data
