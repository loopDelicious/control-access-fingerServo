# Module control-access-fingerservo

Get physical access by moving a servo to an open position upon a fingerprint match.

## Model joyce:control-access-fingerservo:fingerServo

Scanning a fingerprint that is a match using the R503 fingerprint sensor results in moving a servo to an open position.

### Configuration

The following attribute template can be used to configure this model:

```json
{
  "board": <string>,
  "sensor": <string>,
  "servo": <string>,
  "leave_open_timeout": <float>
}
```

#### Attributes

The following attributes are available for this model:

| Name                 | Type   | Inclusion | Description                                                                                               |
| -------------------- | ------ | --------- | --------------------------------------------------------------------------------------------------------- |
| `board`              | string | Required  | Name of the Raspberry Pi board in the Viam app                                                            |
| `sensor`             | string | Required  | Name of the fingerprint sensor component in the Viam app                                                  |
| `servo`              | string | Required  | Name of the servo component in the Viam app                                                               |
| `leave_open_timeout` | float  | Optional  | Time to leave the servo in an open position after a fingerprint match (in seconds), default is 60 seconds |

#### Example Configuration

```json
{
  "sensor": "fingerprint-sensor",
  "board": "board-1",
  "servo": "servo-1",
  "leave_open_timeout", 30
}
```

### DoCommand

Example payload of each command that is supported and the arguments that can be used, to `start` and `stop` the control loop.

#### Example DoCommand

```json
{ "action": "start" }
```

```json
{ "action": "stop" }
```
