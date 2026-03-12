#----------User settings------------------
SKETCH		:= firmwareESP32S3.ino
PORT		:= /dev/ttyUSB0
FQBN		:= esp32:esp32:ep32
BAUD		:= 115200
BUILD_DIR	:= build

#------------Commands-------------------
ARDUINO_CLI	:= arduino-cli

all: compile

compile:
	$(ARDUINO_CLI) compile \
		--fqbn $(FQBN) \
		--output-dir $(BUILD_DIR) \


upload:
	$(ARDUINO_CLI) upload \
		-p $(PORT) \
		---fqbn $(FQBN) \


monitor:
	picocom $(PORT) -b $(BAUD)

board-list:
	$(ARDUINO_CLI) board list

board-search:
	$(ARDUINO_CLI) board install | grep -i esp32

clean:
	rm -rf $(BUILD_DIR)

help:
	@echo "make compile		-build sketch"
	@echo "make upload		-flash board"
	@echo "make monitor		-open serial monitor"
	@echo "make clean		-remove build files"
	@echo "make board_list"
	@echo "make board-search"
