"""Built-in benchmark test suites for RAG performance evaluation.

Contains pre-built evaluation datasets covering educational content
for testing retrieval quality and cross-domain rejection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
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
    """A document to seed the vector store for benchmarking.

    `content` holds inline text for the synthetic suites. `source_path` instead
    points at a real file on disk (PDF/DOCX/…), so a suite can benchmark against
    genuinely messy real-world extraction rather than hand-written prose.
    """
    document_id: str
    filename: str
    content: str = ""
    mime_type: str = "text/plain"
    source_path: Optional[str] = None

    def read_bytes(self) -> bytes:
        if self.source_path:
            return Path(self.source_path).read_bytes()
        return self.content.encode("utf-8")


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
# Suite 4: Lesson-node concepts (what the Planner actually sends at teach time)
# ---------------------------------------------------------------------------
# The other suites use hand-written search queries. In production the retrieval
# query is a LessonNode *concept title* generated by the Planner, which carries
# framing words ("Introduction to…", "Key Concepts:…") that a short dense query
# does not benefit from — the real observed shapes are e.g. "Introduction to the
# Cell and Cell Membrane" and "Key Organelles: Nucleus, Mitochondria, and
# Ribosomes". This suite covers that input shape against the same physics
# document, with ground truth labelled per section (chunks map 1:1 to sections
# 1.1-2.3 of _PHYSICS_DOC).
_LESSON_NODE_QUERIES = [
    BenchmarkQuery(
        query_text="Introduction to Electric Current and Its SI Unit",
        expected_chunk_ids=["chunk_bench_ph_0001"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 1.1 as an intro node title",
    ),
    BenchmarkQuery(
        query_text="Understanding the Fundamentals of Ohm's Law",
        expected_chunk_ids=["chunk_bench_ph_0002"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 1.2 as a core node title",
    ),
    BenchmarkQuery(
        query_text="Key Concepts: Resistance and Resistivity in Conductors",
        expected_chunk_ids=["chunk_bench_ph_0003"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 1.3 with a 'Key Concepts:' prefix",
    ),
    BenchmarkQuery(
        query_text="Overview of Series and Parallel Circuit Configurations",
        expected_chunk_ids=["chunk_bench_ph_0004"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 1.4 with an 'Overview of' prefix",
    ),
    BenchmarkQuery(
        query_text="Core Concept: The Heating Effect of Electric Current",
        expected_chunk_ids=["chunk_bench_ph_0005"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 1.5 with a 'Core Concept:' prefix",
    ),
    BenchmarkQuery(
        query_text="Introduction to Magnetic Fields Around Current-Carrying Conductors",
        expected_chunk_ids=["chunk_bench_ph_0006"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 2.1 as an intro node title",
    ),
    BenchmarkQuery(
        query_text="Understanding Electromagnetic Induction and Faraday's Law",
        expected_chunk_ids=["chunk_bench_ph_0007"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 2.2 as a core node title",
    ),
    BenchmarkQuery(
        query_text="Key Concepts: Electric Motors and Generators Explained",
        expected_chunk_ids=["chunk_bench_ph_0008"],
        expected_risk_level="low",
        category="lesson_node",
        description="Section 2.3 with a 'Key Concepts:' prefix",
    ),
]


# ---------------------------------------------------------------------------
# Suite 5: Real uploaded PDF (genuine extraction, not hand-written prose)
# ---------------------------------------------------------------------------
# The other suites use clean synthetic text. This one benchmarks a PDF a user
# actually uploaded through the app, so the chunks carry real extraction noise:
# content split mid-sentence across page boundaries and section titles detected
# as "where:". Queries are Planner-style node concepts for this document;
# ground truth is labelled from the chunks' actual content.
_REAL_PDF_PATH = (
    Path(__file__).resolve().parents[4]
    / "data/storage/daad7a55972d424b8d50e8e442f5844b"
    / "8d999f0d9e8f41888495c7995fb32c6a.pdf"
)

_REAL_PDF_DOC = BenchmarkDocument(
    document_id="bench_real_newton",
    filename="Newtons_Laws.pdf",
    mime_type="application/pdf",
    source_path=str(_REAL_PDF_PATH),
)

# Chunk map (from the real extraction):
#   _0001 §1 Motion & Force, §2 First Law/inertia, §3 Second Law intro (F = ma)
#   _0002 F = ma terms + worked example, §4 Third Law, §5 relationship of the laws
#   _0003 §6 Everyday applications, §7 Important terms, §8 Summary (start)
#   _0004 Summary tail (net force zero, F = ma, action-reaction)
_REAL_PDF_QUERIES = [
    BenchmarkQuery(
        query_text="Introduction to Motion and Force",
        expected_chunk_ids=["chunk_bench_re_0001"],
        expected_risk_level="low", category="lesson_node",
    ),
    BenchmarkQuery(
        query_text="Understanding Newton's First Law and the Concept of Inertia",
        expected_chunk_ids=["chunk_bench_re_0001"],
        expected_risk_level="low", category="lesson_node",
    ),
    BenchmarkQuery(
        query_text="Key Concepts: Newton's Second Law and the Equation F = ma",
        expected_chunk_ids=["chunk_bench_re_0001", "chunk_bench_re_0002"],
        expected_risk_level="low", category="lesson_node",
    ),
    BenchmarkQuery(
        query_text="Overview of Newton's Third Law: Action and Reaction Pairs",
        expected_chunk_ids=["chunk_bench_re_0002"],
        expected_risk_level="low", category="lesson_node",
    ),
    BenchmarkQuery(
        query_text="Core Concept: How Net Force and Mass Determine Acceleration",
        expected_chunk_ids=["chunk_bench_re_0002"],
        expected_risk_level="low", category="lesson_node",
    ),
    BenchmarkQuery(
        query_text="Everyday Applications of Newton's Laws of Motion",
        expected_chunk_ids=["chunk_bench_re_0003"],
        expected_risk_level="low", category="lesson_node",
    ),
    BenchmarkQuery(
        query_text="Key Terms: Force, Mass, Inertia and Net Force",
        expected_chunk_ids=["chunk_bench_re_0003"],
        expected_risk_level="low", category="lesson_node",
    ),
    BenchmarkQuery(
        query_text="Summary: Relationship Between the Three Laws of Motion",
        expected_chunk_ids=["chunk_bench_re_0002", "chunk_bench_re_0003"],
        expected_risk_level="low", category="lesson_node",
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

LESSON_NODE_SUITE = BenchmarkSuite(
    name="Lesson-Node Concepts",
    description=(
        "8 Planner-style lesson-node concept titles — the query shape production "
        "actually sends — with per-section ground truth on the physics document"
    ),
    documents=[_PHYSICS_DOC],
    queries=_LESSON_NODE_QUERIES,
    config={"top_k": 5, "relevance_threshold": 0.5001, "confidence_threshold": 0.52}
)

REAL_PDF_SUITE = BenchmarkSuite(
    name="Real Uploaded PDF (Newton's Laws)",
    description=(
        "8 Planner-style node concepts against a PDF actually uploaded through the app, "
        "with real extraction noise and per-chunk ground truth"
    ),
    documents=[_REAL_PDF_DOC],
    queries=_REAL_PDF_QUERIES,
    config={"top_k": 5, "relevance_threshold": 0.5001, "confidence_threshold": 0.52}
)

ALL_SUITES = {
    "physics": PHYSICS_SUITE,
    "rejection": REJECTION_SUITE,
    "multilingual": MULTILINGUAL_SUITE,
    "lesson_nodes": LESSON_NODE_SUITE,
    "real_pdf": REAL_PDF_SUITE,
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
