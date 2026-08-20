package org.springframework.samples.petclinic.api;

/** Thrown when a requested resource genuinely doesn't exist — maps to 404. */
public class ResourceNotFoundException extends RuntimeException {

	public ResourceNotFoundException(String message) {
		super(message);
	}

}
