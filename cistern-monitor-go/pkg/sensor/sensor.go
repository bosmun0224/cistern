package sensor

import (
	"fmt" // Using fmt for simple console logging/debug messages for now
	"log" // Standard logger can also be used
)

// Sensor holds configuration relevant to sensor reading and conversion.
// These values are typically derived from the global application configuration.
type Sensor struct {
	ADCChannel   int     // The ADC channel to read from (e.g., 0 for CH0 on MCP3008)
	ADCMaxValue  int     // Maximum possible raw value from the ADC (e.g., 1023 for 10-bit)
	TankHeightCM float64 // Total height of the water tank in centimeters
}

// NewSensor creates and returns a new Sensor instance.
// It requires the ADC channel, the ADC's maximum output value, and the tank's height in CM.
func NewSensor(adcChannel int, adcMaxValue int, tankHeightCM float64) *Sensor {
	if adcMaxValue == 0 {
		log.Println("Warning: ADCMaxValue is 0 in NewSensor, this may lead to division by zero in ConvertToDepth if not handled.")
	}
	return &Sensor{
		ADCChannel:   adcChannel,
		ADCMaxValue:  adcMaxValue,
		TankHeightCM: tankHeightCM,
	}
}

// ReadRawADCValue simulates reading a raw integer value from an Analog-to-Digital Converter (ADC).
// This is a **PLACEHOLDER** function. In a real-world application, this method would
// interact with hardware, for example, by using an SPI communication library (like periph.io/x/conn/v3/spi
// or other platform-specific SDKs) to read data from an ADC chip like an MCP3008.
// The `s.ADCChannel` field would specify which channel on the ADC to read.
func (s *Sensor) ReadRawADCValue() (int, error) {
	// Simulate a sensor reading.
	// In a real scenario, this value would come from the hardware.
	dummyRawValue := 512 // Example: A reading around half-way for a 10-bit ADC (0-1023)

	// Log that this is a placeholder and what it's doing.
	// Using fmt.Printf for now, but a structured logger would be better in production.
	fmt.Printf("INFO: sensor.ReadRawADCValue called for ADC channel %d (PLACEHOLDER)\n", s.ADCChannel)
	fmt.Printf("INFO: Returning dummy ADC value: %d\n", dummyRawValue)

	// In a real implementation, you might encounter errors (e.g., SPI communication failure).
	// return 0, errors.New("failed to read from ADC")
	return dummyRawValue, nil
}

// ConvertToDepth converts a raw ADC integer value to water depth in centimeters.
// The conversion formula assumes a linear relationship between the ADC value and water depth.
// s.ADCMaxValue represents the ADC reading when the tank is full (or at `s.TankHeightCM`).
// s.TankHeightCM is the effective height of the water column that the sensor can measure.
// This function will likely require calibration based on the specific sensor, its positioning,
// and the tank's geometry for accurate readings.
func (s *Sensor) ConvertToDepth(rawValue int) float64 {
	if s.ADCMaxValue == 0 {
		// Prevent division by zero if ADCMaxValue isn't set correctly.
		// Log this error or handle it as appropriate for your application.
		fmt.Println("ERROR: sensor.ConvertToDepth - ADCMaxValue is 0, cannot calculate depth. Returning 0cm.")
		return 0.0
	}

	// Ensure floating-point arithmetic for accurate percentage calculation.
	percentageFull := float64(rawValue) / float64(s.ADCMaxValue)
	depthCM := percentageFull * s.TankHeightCM

	// Clamping the value to be within 0 and TankHeightCM might be useful
	// depending on sensor behavior (e.g. if rawValue can exceed ADCMaxValue due to noise)
	if depthCM < 0 {
		depthCM = 0
	} else if depthCM > s.TankHeightCM {
		depthCM = s.TankHeightCM
		// fmt.Printf("DEBUG: Calculated depth %f cm exceeded TankHeightCM %f cm, clamped.\n", depthCM, s.TankHeightCM)
	}


	fmt.Printf("DEBUG: sensor.ConvertToDepth - Raw: %d, MaxADC: %d, TankHeight: %.2fcm => Depth: %.2fcm\n",
		rawValue, s.ADCMaxValue, s.TankHeightCM, depthCM)

	return depthCM
}
