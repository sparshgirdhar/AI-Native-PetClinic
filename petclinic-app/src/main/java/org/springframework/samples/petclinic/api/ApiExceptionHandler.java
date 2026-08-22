package org.springframework.samples.petclinic.api;

import java.time.Instant;
import java.util.Map;

import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.validation.FieldError;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.RestControllerAdvice;

/**
 * Scoped to org.springframework.samples.petclinic.api only — the existing MVC controllers
 * keep their own HTML-based error handling untouched.
 */
@RestControllerAdvice(basePackages = "org.springframework.samples.petclinic.api")
public class ApiExceptionHandler {

	@ExceptionHandler(ResourceNotFoundException.class)
	public ResponseEntity<Map<String, Object>> handleNotFound(ResourceNotFoundException ex) {
		return ResponseEntity.status(HttpStatus.NOT_FOUND)
			.body(Map.of("timestamp", Instant.now().toString(), "error", "Not Found", "message", ex.getMessage()));
	}

	@ExceptionHandler(IllegalArgumentException.class)
	public ResponseEntity<Map<String, Object>> handleBadRequest(IllegalArgumentException ex) {
		return ResponseEntity.status(HttpStatus.BAD_REQUEST)
			.body(Map.of("timestamp", Instant.now().toString(), "error", "Bad Request", "message", ex.getMessage()));
	}

	@ExceptionHandler(MethodArgumentNotValidException.class)
	public ResponseEntity<Map<String, Object>> handleValidation(MethodArgumentNotValidException ex) {
		String message = ex.getBindingResult()
			.getFieldErrors()
			.stream()
			.map(err -> err.getField() + ": " + err.getDefaultMessage())
			.reduce((a, b) -> a + "; " + b)
			.orElse("Validation failed");
		return ResponseEntity.status(HttpStatus.BAD_REQUEST)
			.body(Map.of("timestamp", Instant.now().toString(), "error", "Bad Request", "message", message));
	}

}
// CI test trigger
