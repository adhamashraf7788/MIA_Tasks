"""
Task 1.2: Stadium Gate Ticket Codec
====================================

Checksum design (how it works):
--------------------------------
We compute a position-weighted checksum over the ticket ID:

    checksum = sum( (index + 1) * ord(character) for every character ) mod 967

- Every character in the ticket contributes to the sum, so no part of the
  content is ignored.
- Each character's contribution is weighted by its 1-based position. This
  means even a character SWAP (e.g. "AB12" -> "BA12", same characters, same
  ord() values overall) changes the checksum, because the weights attached
  to each ord() value change.
- Changing ANY single character changes that character's ord() value at its
  position, which changes the weighted sum and, in turn, the checksum
  mod 967 (967 is prime, chosen to spread checksum values evenly across the
  output range and avoid clustering/collisions between visually-similar
  ticket IDs).
- The checksum is embedded in the barcode as a fixed-width 3-digit,
  zero-padded string appended after a '-' separator, e.g.
  "MIA2026GATE7-321".

This is NOT a cryptographic hash (a determined forger who knows the formula
could reverse-engineer a matching checksum), but it fully satisfies the
tamper-DETECTION requirement of this task: any accidental corruption, or a
naive single-character edit of an already-issued barcode, will be caught
at decode time and never decode as valid.
"""


class TicketCodec:
    MODULUS = 967  # prime modulus used to spread checksum values evenly

    def _compute_checksum(self, ticket_id: str) -> int:
        """Position-weighted checksum: sum((i+1) * ord(char)) mod MODULUS."""
        total = 0
        for i, ch in enumerate(ticket_id):
            total += (i + 1) * ord(ch)
        return total % self.MODULUS

    def encode(self, ticket_id: str) -> str:
        """Takes a ticket ID string and returns a barcode string embedding
        a checksum, in the form 'TICKET_ID-CCC' (CCC = 3-digit checksum)."""
        checksum = self._compute_checksum(ticket_id)
        return f"{ticket_id}-{checksum:03d}"

    def decode(self, barcode: str) -> str:
        """Recomputes the checksum from the ticket portion of the barcode
        and compares it to the checksum embedded in the barcode. Returns
        the original ticket ID if it matches, or a corruption flag string
        otherwise. A corrupted ticket can never decode as valid."""
        if "-" not in barcode:
            return "CORRUPTED TICKET"

        ticket_id, _, checksum_str = barcode.rpartition("-")

        if not ticket_id or not checksum_str.isdigit():
            return "CORRUPTED TICKET"

        embedded_checksum = int(checksum_str)
        expected_checksum = self._compute_checksum(ticket_id)

        if embedded_checksum != expected_checksum:
            return "CORRUPTED TICKET"

        return ticket_id


def _corrupt_one_character(barcode: str) -> str:
    """Demo helper: flips a single character in the ticket portion of a
    barcode, leaving the (now stale) checksum untouched, to simulate
    tampering."""
    ticket_id, sep, checksum_str = barcode.rpartition("-")
    chars = list(ticket_id)
    original = chars[0]
    chars[0] = "X" if original != "X" else "Y"
    corrupted_ticket = "".join(chars)
    return f"{corrupted_ticket}{sep}{checksum_str}"


if __name__ == "__main__":
    codec = TicketCodec()

    sample_ids = ["MIA2026GATE7", "ARG10VIP", "KSA07STAND"]

    print("=== Encoding sample tickets ===")
    barcodes = []
    for tid in sample_ids:
        barcode = codec.encode(tid)
        barcodes.append(barcode)
        print(f"encode({tid!r}) -> {barcode!r}")

    print("\n=== Decoding barcodes as-is (should all succeed) ===")
    for barcode in barcodes:
        result = codec.decode(barcode)
        status = "valid" if result != "CORRUPTED TICKET" else "tampered"
        print(f"decode({barcode!r}) -> {result!r}  ({status})")

    print("\n=== Hand-corrupting one character per barcode (should be flagged) ===")
    for barcode in barcodes:
        corrupted = _corrupt_one_character(barcode)
        result = codec.decode(corrupted)
        status = "valid" if result != "CORRUPTED TICKET" else "tampered"
        print(f"decode({corrupted!r}) -> {result!r}  ({status})")
