package org.example.mcpserver.tools;

import java.time.LocalDate;
import java.time.format.DateTimeParseException;
import java.util.List;

import org.example.mcpserver.client.PetClinicClient;
import org.example.mcpserver.dto.*;
import org.springframework.ai.tool.annotation.Tool;
import org.springframework.stereotype.Component;

@Component
public class PetClinicTools {

	private final PetClinicClient petClinicClient;

	public PetClinicTools(PetClinicClient petClinicClient) {
		this.petClinicClient = petClinicClient;
	}

	@Tool(description = "Find pet owners by their last name")
	public List<OwnerDto> findOwnersByLastName(String lastName) {
		return petClinicClient.findOwnersByLastName(lastName);
	}

	@Tool(description = "Get a pet owner by their ID")
	public OwnerDto getOwnerById(Integer ownerId) {
		return petClinicClient.getOwnerById(ownerId);
	}

	@Tool(description = "Get all available pet types (e.g. dog, cat, bird) that can be used when creating a pet")
	public List<PetTypeDto> getPetTypes() {
		return petClinicClient.getPetTypes();
	}

	@Tool(description = "Get all veterinarians and their specialties")
	public VetListResponse getVets() {
		return petClinicClient.getVets();
	}

	@Tool(description = "Get a pet by owner ID and pet ID")
	public PetDto getPet(Integer ownerId, Integer petId) {
		return petClinicClient.getPet(ownerId, petId);
	}

	@Tool(description = "Get all visits for a pet")
	public List<VisitDto> getPetVisits(Integer ownerId, Integer petId) {
		return List.of(petClinicClient.getPetVisits(ownerId, petId));
	}

	@Tool(description = "Create a new pet owner")
	public OwnerDto createOwner(String firstName, String lastName, String address, String city, String telephone) {
		OwnerDto owner = new OwnerDto(null, firstName, lastName, address, city, telephone);
		return petClinicClient.createOwner(owner);
	}

	@Tool(description = "Create a new pet for an owner. petTypeName should be a common pet type "
		+ "like 'dog', 'cat', 'bird', 'lizard', 'snake', or 'hamster' — call getPetTypes first "
		+ "if unsure which types are valid. birthDate must be in yyyy-MM-dd format, e.g. 2022-01-15.")
	public PetDto createPet(Integer ownerId, String name, String birthDate, String petTypeName) {
		Integer petTypeId = resolvePetTypeId(petTypeName);
		LocalDate parsedBirthDate = parseDate(birthDate, "birthDate");

		PetTypeDto petType = new PetTypeDto(petTypeId, null);
		PetDto pet = new PetDto(null, name, parsedBirthDate, petType);

		return petClinicClient.createPet(ownerId, pet);
	}

	@Tool(description = "Schedule a future visit for a pet. date must be in yyyy-MM-dd format, "
		+ "e.g. 2026-12-12, and must be a future date.")
	public VisitDto createVisit(Integer ownerId, Integer petId, String date, String description) {
		LocalDate parsedDate = parseDate(date, "date");

		if (!parsedDate.isAfter(LocalDate.now())) {
			throw new IllegalArgumentException(
				"Visit date must be in the future. "
					+ "Received: " + parsedDate
			);
		}

		VisitDto visit = new VisitDto(null, parsedDate, description);
		return petClinicClient.createVisit(ownerId, petId, visit);
	}

	/**
	 * Resolves a human-readable pet type name (e.g. "dog") to petclinic-app's internal
	 * numeric id. Case-insensitive. The LLM should never need to know or guess these ids.
	 */
	private Integer resolvePetTypeId(String petTypeName) {
		List<PetTypeDto> types = petClinicClient.getPetTypes();
		return types.stream()
			.filter(t -> t.name() != null && t.name().equalsIgnoreCase(petTypeName.trim()))
			.map(PetTypeDto::id)
			.findFirst()
			.orElseThrow(() -> new IllegalArgumentException("Unknown pet type '" + petTypeName + "'. Valid types are: "
				+ types.stream().map(PetTypeDto::name).toList()
				+ ". Call getPetTypes to see the current list, then retry with an exact match."));
	}

	/**
	 * Parses a date string. On failure, throws a plain IllegalArgumentException with a
	 * clear, corrective message — Spring AI's MethodToolCallback catches exceptions
	 * thrown from inside @Tool methods, wraps them as ToolExecutionException, and by
	 * default sends the message back to the model as tool output. The model then retries
	 * with a corrected value instead of the agent loop breaking.
	 */
	private LocalDate parseDate(String value, String fieldName) {
		try {
			return LocalDate.parse(value);
		}
		catch (DateTimeParseException ex) {
			throw new IllegalArgumentException(
				"Invalid " + fieldName + " '" + value + "'. Expected format is yyyy-MM-dd, e.g. 2026-08-21. "
					+ "Please retry with the date in that exact format.");
		}
	}

}
