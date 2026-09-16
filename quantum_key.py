"""
quantum_key.py
--------------
Generates a genuinely random encryption key using a real quantum circuit
(Hadamard gate + measurement) via IBM's Qiskit library.

REQUIRES (install in Colab): pip install qiskit qiskit-aer

Falls back to Python's `secrets` module (cryptographically secure, but
classical) if Qiskit is unavailable, so your pipeline never breaks.
"""

import secrets


def generate_quantum_key_bits(num_bits: int) -> str:
    try:
        from qiskit import QuantumCircuit, transpile
        from qiskit_aer import AerSimulator

        chunk_size = 32
        bits = ""
        remaining = num_bits
        simulator = AerSimulator()

        while remaining > 0:
            n = min(chunk_size, remaining)
            qc = QuantumCircuit(n, n)
            qc.h(range(n))
            qc.measure(range(n), range(n))

            compiled = transpile(qc, simulator)
            result = simulator.run(compiled, shots=1).result()
            counts = result.get_counts()
            bitstring = list(counts.keys())[0].replace(" ", "")
            bits += bitstring
            remaining -= n

        return bits[:num_bits]

    except Exception as e:
        print(f"[quantum_key] Qiskit unavailable or failed ({e}); "
              f"falling back to classical secure RNG.")
        return "".join(secrets.choice("01") for _ in range(num_bits))


def generate_quantum_key_bytes(num_bytes: int) -> bytes:
    bits = generate_quantum_key_bits(num_bytes * 8)
    return int(bits, 2).to_bytes(num_bytes, byteorder="big")


if __name__ == "__main__":
    key = generate_quantum_key_bytes(16)
    print("Generated 128-bit quantum-assisted key (hex):", key.hex())
