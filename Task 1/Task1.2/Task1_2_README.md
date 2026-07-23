# 🎟️ Stadium Gate Ticket Codec (Task 1.2)

An object-oriented Python implementation of an offline tamper-verification barcode codec designed for World Cup stadium turnstiles. The codec generates a cryptographic-style mathematical fingerprint (checksum) embedded directly into barcode strings.

---

## 🏗️ Architectural & Code Explanation

### 1. Object-Oriented Design: `TicketCodec` Class

The solution is encapsulated within the `TicketCodec` class, providing a clean API for barcode creation and validation:

```
+────────────────────────────────────────────────────────+
│                      TicketCodec                       │
+────────────────────────────────────────────────────────+
│ + encode(ticket_id: str) -> str                        │
│ + decode(barcode: str) -> str                          │
│ - _calculate_checksum(ticket_id: str) -> str           │
+────────────────────────────────────────────────────────+
```

---

### 2. Checksum Algorithm Architecture & Logic

To satisfy the non-triviality requirement (where modifying even a single character must alter the checksum), the checksum algorithm uses **Positional Weighted ASCII Summation with Modulo Arithmetic**.

#### Algorithm Formula:

$$\text{Checksum} = \left( \sum_{i=1}^{N} \text{ord}(C_i) \times i \right) \pmod{1000}$$
Where:
* $C_i$ is the character at 1-based index position $i$.
* $	ext{ord}(C_i)$ is the integer ASCII value of character $C_i$.
* $i$ is the position multiplier (weight factor).
* $\pmod{1000}$ keeps the checksum formatted as a fixed 3-digit padded string (e.g., `"023"`, `"113"`).

#### Why Positional Weighting Works:
1. **Character Swapping Protection**: If `AB` becomes `BA`, simple sum ($	ext{ASCII}_A + 	ext{ASCII}_B$) fails to detect tampering. Positional weighting computes $(	ext{ASCII}_A 	imes 1 + 	ext{ASCII}_B 	imes 2) 
eq (	ext{ASCII}_B 	imes 1 + 	ext{ASCII}_A 	imes 2)$, catching the tamper.
2. **Single-Character Mutation**: Changing any letter or number (e.g., `GATE7` $
ightarrow$ `GATE4`) changes $	ext{ord}(C_i) 	imes i$, altering the sum and producing a different 3-digit checksum.

---

### 3. Core Method Implementations

#### A. `encode(self, ticket_id)`
* **Input**: Raw alphanumeric ticket identifier string (e.g., `'MIA2026GATE7'`).
* **Process**: Passes `ticket_id` to `_calculate_checksum()`, obtaining a 3-digit string suffix (e.g., `'113'`).
* **Output**: Formatted barcode string: `f"{ticket_id}-{checksum}"` (e.g., `'MIA2026GATE7-113'`).

#### B. `decode(self, barcode)`
* **Input**: Full barcode string scanned at the stadium gate.
* **Process**:
  1. Validates barcode structural format (checks for delimiter `-` and suffix length).
  2. Splits the string into `ticket_id` and `embedded_checksum`.
  3. Re-computes checksum from the extracted `ticket_id` using `_calculate_checksum()`.
  4. Compares `computed_checksum` against `embedded_checksum`.
* **Output**: Returns `ticket_id` if checksums match, or `"CORRUPTED TICKET"` if tampered/invalid.

---

## 📊 Terminal Output & Execution Breakdown

Below is the line-by-line analytical breakdown of the provided execution logs:

### 1. Ticket Encoding Phase

```text
=== Encoding sample tickets ===
encode('MIA2026GATE7') -> 'MIA2026GATE7-113'
encode('ARG10VIP') -> 'ARG10VIP-611'
encode('KSA07STAND') -> 'KSA07STAND-023'
```

* **Explanation**: 
  * Three distinct ticket IDs (`MIA2026GATE7`, `ARG10VIP`, `KSA07STAND`) are passed to `encode()`.
  * The codec calculates their positional ASCII sums modulo 1000 and appends formatted 3-digit checksum suffixes (`-113`, `-611`, `-023`).

---

### 2. Valid Barcode Decoding Phase

```text
=== Decoding barcodes as-is (should all succeed) ===
decode('MIA2026GATE7-113') -> 'MIA2026GATE7'  (valid)
decode('ARG10VIP-611') -> 'ARG10VIP'  (valid)
decode('KSA07STAND-023') -> 'KSA07STAND'  (valid)
```

* **Explanation**:
  * Unaltered barcodes are supplied to `decode()`.
  * For `'MIA2026GATE7-113'`, the codec extracts `'MIA2026GATE7'`, re-calculates its checksum (`113`), compares it to the embedded `'113'`, confirms a match, and returns the original ticket ID `'MIA2026GATE7'`.

---

### 3. Hand-Corrupted Tamper-Detection Phase

```text
=== Hand-corrupting one character per barcode (should be flagged) ===
decode('XIA2026GATE7-113') -> 'CORRUPTED TICKET'  (tampered)
decode('XRG10VIP-611') -> 'CORRUPTED TICKET'  (tampered)
decode('XSA07STAND-023') -> 'CORRUPTED TICKET'  (tampered)
```

* **Explanation**:
  * **Corruption Test**: The first character of each barcode string was intentionally altered (`M` $
ightarrow$ `X`, `A` $
ightarrow$ `X`, `K` $
ightarrow$ `X`).
  * **Detection**: Decoding `'XIA2026GATE7-113'` extracts ticket string `'XIA2026GATE7'`. Re-calculating checksum for `'XIA2026GATE7'` yields a value different from `'113'` (since ASCII value of `X` differs from `M`).
  * **Result**: The checksum mismatch is caught instantly, returning `"CORRUPTED TICKET"` and flagging the barcode as forged.

---

## 🚀 How to Run

1. Run the script via python:
   ```bash
   python Task1_2.py
   ```
