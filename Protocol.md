Protocol

AA 55  <type:1>  <len:2 little-endian>  <payload:len bytes>  <crc16:2>   (optional crc, recommended later)

For the moment we will keep it simple
AA 55  <type:1>  <payload...>

Packet types we’ll implement now (fixed lengths)

ACK (command accepted)

Header: AA 55 0x10

Payload: cmd_id (1 byte)
Total = 2+1+1 = 4 bytes

ERROR (command rejected)

Header: AA 55 0x11

Payload: cmd_id (1 byte), err_code (1 byte)
Total = 5 bytes

COORDS (counts + mm)

Header: AA 55 0x20

Payload:

int32 x_cnt, y_cnt, z_cnt

float x_mm, y_mm, z_mm (IEEE754 32-bit)
Total payload = 12 + 12 = 24 bytes; total packet = 27 bytes

MOVE DONE

Header: AA 55 0x21

Payload: same as COORDS (end position)
Total = 27 bytes

ZERO DONE

Header: AA 55 0x22

Payload: same as COORDS
Total = 27 bytes
