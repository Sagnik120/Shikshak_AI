"""Built-in benchmark test suites for RAG performance evaluation.

Contains pre-built evaluation datasets covering educational content
for testing retrieval quality and cross-domain rejection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class BenchmarkQuery:
    """A single benchmark query with expected ground-truth results."""
    query_text: str
    expected_chunk_ids: List[str] = field(default_factory=list)
    expected_risk_level: Optional[str] = None
    category: str = ""
    description: str = ""


@dataclass
class BenchmarkDocument:
    """A document to seed the vector store for benchmarking."""
    document_id: str
    filename: str
    content: str
    mime_type: str = "text/plain"


@dataclass
class BenchmarkSuite:
    """A complete benchmark test suite with documents and queries."""
    name: str
    description: str
    documents: List[BenchmarkDocument] = field(default_factory=list)
    queries: List[BenchmarkQuery] = field(default_factory=list)
    config: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Suite 1: Physics NCERT (Educational domain — positive retrieval)
# ---------------------------------------------------------------------------
_PHYSICS_DOC = BenchmarkDocument(
    document_id="bench_physics_001",
    filename="physics_chapter.txt",
    content="""Chapter 1: Electric Current and Circuits

1.1 Electric Current
Electric current is defined as the rate of flow of electric charge through a conductor.
The SI unit of electric current is the ampere (A). One ampere is defined as one coulomb
of charge passing through a cross-section of a conductor in one second.
Mathematically, I = Q/t where I is current, Q is charge, and t is time.

1.2 Ohm's Law
Ohm's Law states that the current flowing through a conductor is directly proportional
to the potential difference across its ends, provided the temperature remains constant.
V = IR, where V is voltage in volts, I is current in amperes, and R is resistance in ohms.
Georg Simon Ohm discovered this fundamental relationship in 1827.

1.3 Resistance and Resistivity
Resistance is the property of a conductor that opposes the flow of electric current.
The SI unit of resistance is the ohm (Ω). Resistance depends on the length of the conductor,
cross-sectional area, temperature, and the nature of the material.
Resistivity (ρ) is defined as R = ρL/A where L is length and A is cross-sectional area.
Good conductors like copper have low resistivity, while insulators like rubber have high resistivity.

1.4 Series and Parallel Circuits
In a series circuit, components are connected end-to-end, and the same current flows
through each component. The total resistance is the sum of individual resistances:
R_total = R1 + R2 + R3.
In a parallel circuit, components are connected across the same two points. The voltage
across each component is the same. 1/R_total = 1/R1 + 1/R2 + 1/R3.

1.5 Heating Effect of Electric Current
When electric current flows through a resistor, electrical energy is converted into heat energy.
This is known as the Joule heating effect or Joule's law of heating.
The heat produced H = I²Rt, where I is current, R is resistance, and t is time in seconds.
Applications include electric heaters, electric irons, and incandescent light bulbs.

Chapter 2: Magnetic Effects of Electric Current

2.1 Magnetic Field
A magnetic field is a region around a magnet or current-carrying conductor where
a magnetic force is experienced. Magnetic field lines are used to represent the magnetic
field. They go from north pole to south pole outside the magnet.
Hans Christian Oersted discovered in 1820 that a current-carrying conductor produces
a magnetic field around it.

2.2 Electromagnetic Induction
When a conductor moves in a magnetic field or when the magnetic field around a conductor
changes, an electromotive force (EMF) is induced in the conductor. This phenomenon is
called electromagnetic induction. Michael Faraday discovered this in 1831.
Faraday's law states that the induced EMF is proportional to the rate of change of
magnetic flux through the circuit.

2.3 Electric Motor and Generator
An electric motor converts electrical energy into mechanical energy using the magnetic
effect of current. It works on the principle that a current-carrying conductor placed
in a magnetic field experiences a force.
An electric generator converts mechanical energy into electrical energy based on
electromagnetic induction. It works on the principle of Faraday's law.
""",
)

_PHYSICS_QUERIES = [
    BenchmarkQuery(
        query_text="What is electric current and what is its SI unit?",
        expected_chunk_ids=[],  # Will be populated during benchmark seeding
        expected_risk_level="low",
        category="direct_match",
        description="Direct concept lookup"
    ),
    BenchmarkQuery(
        query_text="Explain Ohm's Law and the relationship between voltage, current and resistance",
        expected_chunk_ids=[],
        expected_risk_level="low",
        category="direct_match",
        description="Core formula lookup"
    ),
    BenchmarkQuery(
        query_text="How does resistance depend on length and area of a conductor?",
        expected_chunk_ids=[],
        expected_risk_level="low",
        category="direct_match",
        description="Resistivity concept"
    ),
    BenchmarkQuery(
        query_text="What is the difference between series and parallel circuits?",
        expected_chunk_ids=[],
        expected_risk_level="low",
        category="direct_match",
        description="Circuit comparison"
    ),
    BenchmarkQuery(
        query_text="Who discovered electromagnetic induction and when?",
        expected_chunk_ids=[],
        expected_risk_level="low",
        category="factual_lookup",
        description="Historical fact"
    ),
    BenchmarkQuery(
        query_text="H = I²Rt formula explanation",
        expected_chunk_ids=[],
        expected_risk_level="low",
        category="formula_lookup",
        description="Joule heating formula"
    ),
    BenchmarkQuery(
        query_text="How does an electric motor work?",
        expected_chunk_ids=[],
        expected_risk_level="low",
        category="concept_explanation",
        description="Motor principle"
    ),
    BenchmarkQuery(
        query_text="Oersted experiment magnetic field",
        expected_chunk_ids=[],
        expected_risk_level="low",
        category="keyword_search",
        description="Sparse keyword retrieval test"
    ),
]


# ---------------------------------------------------------------------------
# Suite 2: Cross-Domain Rejection (must flag high hallucination risk)
# ---------------------------------------------------------------------------
_REJECTION_QUERIES = [
    BenchmarkQuery(
        query_text="What were the main causes of World War 2?",
        expected_chunk_ids=[],
        expected_risk_level="high_hallucination_risk",
        category="cross_domain",
        description="History query on physics doc"
    ),
    BenchmarkQuery(
        query_text="How to make pasta carbonara recipe",
        expected_chunk_ids=[],
        expected_risk_level="high_hallucination_risk",
        category="cross_domain",
        description="Cooking query on physics doc"
    ),
    BenchmarkQuery(
        query_text="Python programming loops and functions tutorial",
        expected_chunk_ids=[],
        expected_risk_level="high_hallucination_risk",
        category="cross_domain",
        description="Programming query on physics doc"
    ),
    BenchmarkQuery(
        query_text="Best investment strategies for 2024 stock market",
        expected_chunk_ids=[],
        expected_risk_level="high_hallucination_risk",
        category="cross_domain",
        description="Finance query on physics doc"
    ),
]


# ---------------------------------------------------------------------------
# Suite 3: Multilingual / Paraphrase (tests cross-lingual retrieval)
# ---------------------------------------------------------------------------
_MULTILINGUAL_QUERIES = [
    BenchmarkQuery(
        query_text="bijli ka pravaah kya hai",
        expected_chunk_ids=[],
        expected_risk_level=None,  # May be low or moderate_relevance
        category="hinglish",
        description="Hinglish: What is electric current"
    ),
    BenchmarkQuery(
        query_text="vidyut dhara ka SI matrak",
        expected_chunk_ids=[],
        expected_risk_level=None,
        category="hinglish",
        description="Hinglish: SI unit of current"
    ),
    BenchmarkQuery(
        query_text="voltage aur current ka relationship batao",
        expected_chunk_ids=[],
        expected_risk_level=None,
        category="hinglish",
        description="Hinglish: Ohm's Law paraphrase"
    ),
    BenchmarkQuery(
        query_text="Tell me about the flow of electrons through wires and how we measure it",
        expected_chunk_ids=[],
        expected_risk_level=None,
        category="paraphrase",
        description="Conversational paraphrase of electric current"
    ),
]


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
PHYSICS_SUITE = BenchmarkSuite(
    name="Physics NCERT",
    description="8 positive retrieval queries on a physics textbook chapter covering electricity and magnetism",
    documents=[_PHYSICS_DOC],
    queries=_PHYSICS_QUERIES,
    config={"top_k": 5, "relevance_threshold": 0.5001, "confidence_threshold": 0.52}
)

REJECTION_SUITE = BenchmarkSuite(
    name="Cross-Domain Rejection",
    description="4 out-of-domain queries that must be rejected with high_hallucination_risk on the physics document",
    documents=[_PHYSICS_DOC],
    queries=_REJECTION_QUERIES,
    config={"top_k": 5, "relevance_threshold": 0.5001, "confidence_threshold": 0.52}
)

MULTILINGUAL_SUITE = BenchmarkSuite(
    name="Multilingual Paraphrase",
    description="4 Hinglish/paraphrased queries testing cross-lingual retrieval on the physics document",
    documents=[_PHYSICS_DOC],
    queries=_MULTILINGUAL_QUERIES,
    config={"top_k": 5, "relevance_threshold": 0.5001, "confidence_threshold": 0.52}
)

ALL_SUITES = {
    "physics": PHYSICS_SUITE,
    "rejection": REJECTION_SUITE,
    "multilingual": MULTILINGUAL_SUITE,
}


def get_suite(name: str) -> BenchmarkSuite:
    """Get a benchmark suite by name."""
    suite = ALL_SUITES.get(name.lower())
    if suite is None:
        raise ValueError(f"Unknown suite '{name}'. Available: {list(ALL_SUITES.keys())}")
    return suite


def list_suites() -> List[Dict[str, str]]:
    """List all available benchmark suites with metadata."""
    return [
        {
            "name": s.name,
            "key": key,
            "description": s.description,
            "num_queries": len(s.queries),
            "num_documents": len(s.documents),
        }
        for key, s in ALL_SUITES.items()
    ]
