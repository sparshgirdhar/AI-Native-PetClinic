package org.example.mcpserver.dto;

import java.util.List;

public record OwnerDto(
	Integer id,
	String firstName,
	String lastName,
	String address,
	String city,
	String telephone,
	List<PetDto> pets
) {

	/**
	 * Convenience constructor for creating a new owner, where there's no pets list yet.
	 * Defaults pets to an empty list rather than null — this DTO also serves as the POST
	 * request body, and an explicit "pets": null could cause issues deserializing into
	 * petclinic-app's Owner entity, whose pets field is a final, no-setter collection.
	 */
	public OwnerDto(Integer id, String firstName, String lastName, String address, String city, String telephone) {
		this(id, firstName, lastName, address, city, telephone, List.of());
	}
}
