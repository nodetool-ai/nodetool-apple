from __future__ import annotations

from typing import Any

from pydantic import Field

try:
    import Contacts  # type: ignore
except Exception:  # pragma: no cover
    Contacts = None  # type: ignore

from nodetool.workflows.base_node import BaseNode
from nodetool.workflows.processing_context import ProcessingContext


class SearchContacts(BaseNode):
    """
    Search macOS Contacts using the Contacts framework (CNContactStore).
    contacts, macos, automation, retrieval

    Use cases:
    - Resolve a human name to emails/phone numbers before messaging
    - Build “who should I notify?” flows for agents
    - Enrich workflow context with contact details
    """

    query: str = Field(default="", description="Name/email/phone substring to search")
    limit: int = Field(default=10, ge=0, description="Maximum contacts to return")
    include_emails: bool = Field(default=True, description="Include email addresses")
    include_phones: bool = Field(default=True, description="Include phone numbers")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["query", "limit"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    @staticmethod
    def _require_contacts():
        if Contacts is None:  # pragma: no cover
            raise RuntimeError(
                "Contacts framework is not available. Install `pyobjc-framework-Contacts`."
            )

    @staticmethod
    def _contact_to_dict(
        contact: Any, include_emails: bool, include_phones: bool
    ) -> dict:
        emails: list[str] = []
        phones: list[str] = []

        if include_emails:
            for item in contact.emailAddresses() or []:  # type: ignore
                try:
                    emails.append(str(item.value()))  # type: ignore
                except Exception:
                    continue

        if include_phones:
            for item in contact.phoneNumbers() or []:  # type: ignore
                try:
                    phones.append(str(item.value().stringValue()))  # type: ignore
                except Exception:
                    continue

        given = str(contact.givenName() or "")  # type: ignore
        family = str(contact.familyName() or "")  # type: ignore
        full = " ".join([p for p in [given, family] if p]).strip()

        return {
            "identifier": str(contact.identifier()),  # type: ignore
            "given_name": given,
            "family_name": family,
            "full_name": full,
            "emails": emails,
            "phones": phones,
        }

    async def process(self, context: ProcessingContext) -> list[dict]:
        self._require_contacts()
        if not self.query.strip():
            return []

        store = Contacts.CNContactStore.alloc().init()  # type: ignore
        keys = [
            Contacts.CNContactIdentifierKey,  # type: ignore
            Contacts.CNContactGivenNameKey,  # type: ignore
            Contacts.CNContactFamilyNameKey,  # type: ignore
        ]
        if self.include_emails:
            keys.append(Contacts.CNContactEmailAddressesKey)  # type: ignore
        if self.include_phones:
            keys.append(Contacts.CNContactPhoneNumbersKey)  # type: ignore

        predicate = Contacts.CNContact.predicateForContactsMatchingName_(  # type: ignore
            self.query
        )
        contacts, error = store.unifiedContactsMatchingPredicate_keysToFetch_error_(  # type: ignore
            predicate, keys, None
        )
        if error is not None:
            raise RuntimeError(f"Contacts search failed: {error}")

        results = [
            self._contact_to_dict(c, self.include_emails, self.include_phones)
            for c in (contacts or [])
        ]
        if self.limit:
            results = results[: self.limit]
        return results


class GetContactByIdentifier(BaseNode):
    """
    Fetch a specific macOS Contact by identifier (CNContactStore).
    contacts, macos, automation, retrieval

    Use cases:
    - Round-trip: SearchContacts → pick identifier → fetch full details
    - Store a stable reference to a person in a workflow
    """

    identifier: str = Field(default="", description="CNContact identifier")
    include_emails: bool = Field(default=True, description="Include email addresses")
    include_phones: bool = Field(default=True, description="Include phone numbers")

    @classmethod
    def get_basic_fields(cls) -> list[str]:
        return ["identifier"]

    @classmethod
    def is_cacheable(cls) -> bool:
        return True

    async def process(self, context: ProcessingContext) -> dict:
        SearchContacts._require_contacts()
        if not self.identifier.strip():
            return {}

        store = Contacts.CNContactStore.alloc().init()  # type: ignore
        keys = [
            Contacts.CNContactIdentifierKey,  # type: ignore
            Contacts.CNContactGivenNameKey,  # type: ignore
            Contacts.CNContactFamilyNameKey,  # type: ignore
        ]
        if self.include_emails:
            keys.append(Contacts.CNContactEmailAddressesKey)  # type: ignore
        if self.include_phones:
            keys.append(Contacts.CNContactPhoneNumbersKey)  # type: ignore

        contact, error = store.unifiedContactWithIdentifier_keysToFetch_error_(  # type: ignore
            self.identifier, keys, None
        )
        if error is not None:
            raise RuntimeError(f"Failed to fetch contact: {error}")
        if contact is None:
            return {}

        return SearchContacts._contact_to_dict(
            contact, self.include_emails, self.include_phones
        )
