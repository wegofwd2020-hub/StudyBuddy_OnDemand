# Visual Enhancement Audit — All Grades, All Streams

> Curriculum-wide assessment of visual enhancement opportunity across the 218
> canonical units in `data/grade*.json`. Each row recommends **Option 2**
> (per-example SVG / diagram catalogue) or **Option 3** (Remotion explainer
> video) — the two production-ready idioms vetted in the morning's
> [`G11-MATH-001`](g11-science/G11-MATH-001_Sets_and_Functions/) and
> [`G11-PHYS-002`](g11-science/G11-PHYS-002_Kinematics/) reference exemplars.
>
> Companion deep-dive (G11 Science, 29 units): [`g11-science/visual_enhancement_plan.md`](g11-science/visual_enhancement_plan.md).
>
> **Scope:** 218 units across 17 canonical curriculum files. CBSE-prefixed
> duplicates (`cbse_grade*.json`) are excluded; they are older drafts of the
> same content. `grade11_science.json` is excluded — already covered in the
> dedicated G11 Science plan above.

## Reading the recommendation

| Column | Meaning |
|---|---|
| **Visual primitives** | What the unit's visual asks the student to see |
| **Option** | `2` — static SVG / diagram catalogue (default). `3` — Remotion explainer video. `2 + 3` — heavy catalogue plus one or two marquee animations. `none` — text-driven, visuals add noise |
| **Lift** | S / M / L — how much visualisation moves comprehension. L = makes the unit click; M = clarifies significantly; S = nice-to-have |
| **Effort** | S / M / L — authoring cost. S = <5 visuals. M = 5–15. L = >15 or new generator |

**Default rule.** Option 2 unless the concept *is* motion — trajectory, propagation, oscillation, cycle, transition, formation. In those cases Option 3 (with `useCurrentFrame()`-driven Remotion) earns its render cost.

---

## Build-priority summary (top of mind)

Ranked by **lift × audience size ÷ effort**. Use this to pick the next 5–10 units to hand-author after the two reference exemplars.

| Rank | Unit | Why it's near the top |
|---|---|---|
| 1 | **G11-PHYS-010** Oscillations & Waves *(g11-science)* | Highest visual-lift physics topic; every section animates; Doppler is the canonical clip. |
| 2 | **G9-SCI-001** Kinematics 1D | Foundation unit, very large audience (every G9 student); same scaffolding as G11-PHYS-002. |
| 3 | **G11-CHEM-002** Structure of Atom *(g11-science)* | Bohr-model transitions + orbital shapes — first chemistry primitive set for the library. |
| 4 | **G11-MATH-004** Calculus *(generic g11)* + **G11-MATH-002/003** *(generic g11)* | Limits / tangent-line / area-under-curve are animation-defining; one Remotion clip per unit. |
| 5 | **G6-SCI-001** Cells | First biology-anatomy primitives; reusable across G7-SCI-003, G9-SCI-005, G12-BIO-*. |
| 6 | **G12-PHYS-002** Current Electricity / **G8-SCI-003** Electricity & Magnetism | Circuit-schematic generator; same template covers G6-ENG-002, G10-ENG-002, G11-ENG-003. |
| 7 | **G7-SCI-001** Atoms & Periodic Table | Periodic-trend heatmap is high-leverage and reused in G11-CHEM-003. |
| 8 | **G8-SCI-002** Waves: Light & Sound | Wave-superposition Remotion sets up G11-PHYS-010 + G12-PHYS-005. |
| 9 | **G12-PHYS-005** Optics (ray + wave) | Ray-tracing diagrams + diffraction patterns; canonical physics SVG library. |
| 10 | **G12-CHEM-002** Electrochemistry / **G11-SCI-004** | Galvanic-cell schematics, half-reactions; chemistry-schematic generator template. |

---

## Per-curriculum tables

### Grade 5 — STEM (`grade5_stem.json`, 18 units)

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G5-MATH-001 | Place Value and Number Systems | Place-value blocks, number-line | **2** | M | S | Manipulative-style SVG; reuse a place-value block generator. |
| G5-MATH-002 | Fractions and Decimals | Fraction bars, area models, number-line | **2** | L | S | Fraction-bar SVG generator is the canonical primary-grade visual. |
| G5-MATH-003 | Geometry and Measurement | 2D / 3D shape labels, area / perimeter overlays | **2** | L | M | Each shape an SVG; reuse a "labeled polygon" generator. |
| G5-MATH-004 | Data and Statistics | Bar / line / pictograph; mean-median-mode strip | **2** | M | S | Static plots only — no slider needed at this level. |
| G5-MATH-005 | Algebraic Thinking | Pattern strips, balance diagrams | **2** | M | S | Balance-scale SVG to introduce equation-equality. |

#### Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G5-SCI-001 | Matter and Its Properties | States diagrams, phase-change SVG | **2 + 3** | L | M | Phase-change Remotion clip (ice → water → vapour) is unforgettable. |
| G5-SCI-002 | Forces and Motion | Push / pull arrows, balanced-vs-unbalanced FBDs | **2** | L | S | Reuse PHYS-002 Kinematics' arrow-diagram generator. |
| G5-SCI-003 | Ecosystems | Food-web SVG, habitat illustrations | **2** | L | M | Food-web SVG is the canonical biology primitive at this level. |
| G5-SCI-004 | Earth and Space | Solar-system layout, moon-phase cycle | **2 + 3** | L | M | Moon-phase Remotion (28-day cycle) is high-leverage. |
| G5-SCI-005 | Weather and Climate | Water-cycle SVG, climate-zone map | **2** | L | M | Water-cycle SVG with directed arrows; reusable to G6-SCI-005. |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G5-TECH-001 | Introduction to Computing | Hardware-vs-software diagram, IPO model | **2** | M | S | Single SVG showing input → process → output. |
| G5-TECH-002 | Digital Citizenship | Iconography of safety patterns | **none** | S | S | Prose-driven; visuals add little. |
| G5-TECH-003 | Block-Based Programming | Scratch-block screenshots, sequence flow | **2** | M | M | Mock Scratch blocks as SVG (avoid dependency on the live Scratch site). |
| G5-TECH-004 | Data and Information | Spreadsheet sketch, simple chart | **2** | S | S | Mostly tables — markdown-native is enough. |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G5-ENG-001 | Design Thinking Process | 5-step cycle diagram | **2** | M | S | One Mermaid cycle is enough. |
| G5-ENG-002 | Simple Machines | Lever / pulley / inclined-plane SVG | **2 + 3** | L | M | Each machine an SVG; one mechanical-advantage Remotion clip. |
| G5-ENG-003 | Structures and Materials | Bridge / tower diagrams, force arrows | **2** | M | M | Reuse FBD primitives from G5-SCI-002. |
| G5-ENG-004 | Environmental Engineering | Case-study illustrations | **none** | S | S | Reading-driven. |

---

### Grade 6 — STEM (`grade6_stem.json`, 17 units)

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G6-MATH-001 | Ratios and Proportional Relationships | Ratio-bar diagrams, double number-line | **2** | M | S | Reuse fraction-bar generator from G5. |
| G6-MATH-002 | Integers and Rational Numbers | Number-line with negatives, coordinate plane | **2** | M | S | Coordinate-plane SVG generator; reused everywhere. |
| G6-MATH-003 | Expressions and Equations | Algebra-tile diagrams | **2** | M | M | Algebra-tile SVG generator; new primitive. |
| G6-MATH-004 | Geometry | Polygon area overlays, prism nets | **2** | L | M | Prism-net "unfold" is a candidate Remotion clip but Option 2 is enough. |
| G6-MATH-005 | Statistics and Probability | Box plot, histograms | **2** | M | S | Static plots; no interaction needed. |

#### Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G6-SCI-001 | Cells | Labeled animal / plant cell SVG, organelle callouts | **2** | L | L | **Foundational anatomy primitive** — reused across G7-SCI-003, G9-SCI-005, G12-BIO-*. Worth investing in a generator. |
| G6-SCI-002 | Energy Forms and Transformations | Energy-flow Sankey-style diagrams | **2 + 3** | L | M | Energy-transformation animation (PE → KE → heat) earns the clip. |
| G6-SCI-003 | Earth's Layers and Plate Tectonics | Cross-section diagrams, plate-boundary types | **2 + 3** | L | M | Plate-motion Remotion (convergent / divergent / transform) is high-leverage. |
| G6-SCI-004 | Rocks, Minerals and the Rock Cycle | Rock samples (illustrated SVG), cycle diagram | **2 + 3** | L | M | Rock-cycle Remotion is the canonical earth-science animation. |
| G6-SCI-005 | Interdependence in Ecosystems | Nutrient-cycle SVG (carbon, nitrogen, water) | **2 + 3** | L | M | Carbon / nitrogen-cycle Remotion clips reusable to G8-SCI-005, G11-BIO. |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G6-TECH-001 | Introduction to Python | Code blocks, control-flow diagrams | **2** | S | S | Code-block syntax-highlighting is markdown-native. |
| G6-TECH-002 | Internet and Networks | Client-server SVG, DNS lookup flow | **2 + 3** | M | M | DNS-lookup Remotion (sequence of hops) is a memorable explainer. |
| G6-TECH-003 | Creating with Media | Iconography only | **none** | S | S | Prose + screenshots. |
| G6-TECH-004 | Spreadsheets and Data Analysis | Spreadsheet screenshots, chart examples | **2** | S | S | Markdown tables suffice. |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G6-ENG-001 | Forces and Structural Design | Tension / compression / torsion diagrams | **2** | L | M | Reuse FBD primitives. |
| G6-ENG-002 | Electronics Basics | Circuit schematic SVG | **2** | L | L | **Foundational circuit-schematic generator** — reused in G8-SCI-003, G10-ENG-002, G11-ENG-003, G12-PHYS-002. |
| G6-ENG-003 | Robotics Introduction | Robot anatomy diagrams, sensor / actuator icons | **2** | M | M | Static SVG of a labeled robot. |
| G6-ENG-004 | Sustainable Design | Lifecycle flow diagrams | **2** | M | S | Mermaid cycle is enough. |

---

### Grade 7 — STEM (`grade7_stem.json`, 19 units)

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G7-MATH-001 | Proportional Relationships and Percents | Bar-model proportion, percent-strip | **2** | M | S | Reuse ratio-bar from G6. |
| G7-MATH-002 | Operations with Rational Numbers | Number-line operations | **2** | M | S | Number-line generator extension. |
| G7-MATH-003 | Expressions, Equations, Inequalities | Inequality on number-line, balance scale | **2** | M | S | Reuse balance scale + number-line. |
| G7-MATH-004 | Geometry: Angles, Triangles, Scale | Angle-arc SVG, triangle congruence cases | **2** | L | M | Triangle-congruence cards (SSS / SAS / ASA / AAS / RHS) — high-reuse generator. |
| G7-MATH-005 | Probability and Sampling | Tree diagrams, sample-space tables | **2** | M | S | Mermaid trees + tables. |

#### Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G7-SCI-001 | Atoms, Elements, Periodic Table | Atom-shell SVG, periodic-trend heatmap | **2 + 3** | L | M | Heatmap reused in G11-CHEM-003. Bohr-shell Remotion (electron-fill order) is high-leverage. |
| G7-SCI-002 | Chemical Reactions | Particle-collision diagrams | **2 + 3** | L | M | Collision Remotion (reactant → product). |
| G7-SCI-003 | Human Body Systems | Anatomy SVGs (digestive / circulatory / respiratory) | **2** | L | L | Reuse cell-SVG generator scale-up; one anatomy SVG per system. |
| G7-SCI-004 | Genetics and Heredity | Punnett squares, DNA double-helix | **2 + 3** | L | M | Punnett-square SVG + helix Remotion (rotation reveal). |
| G7-SCI-005 | Natural Disasters | Cross-section diagrams, hazard maps | **2** | M | M | Static cross-sections; reuse from G6-SCI-003. |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G7-TECH-001 | Python: Conditionals and Loops | Flowchart of branching | **2** | M | S | Mermaid flowchart per concept. |
| G7-TECH-002 | Python: Functions and Modules | Function-call diagrams | **2** | M | S | Mermaid + code blocks. |
| G7-TECH-003 | Cybersecurity Fundamentals | Iconography, attack-surface diagrams | **2** | S | S | Mostly prose. |
| G7-TECH-004 | Introduction to Databases | Table relationship diagrams | **2** | M | S | ERD-style SVG; markdown tables for queries. |
| G7-TECH-005 | AI Concepts | Conceptual diagrams (ML pipeline) | **2** | M | S | Mermaid pipeline diagram is enough. |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G7-ENG-001 | Mechanisms and Gears | Gear meshing diagrams, cam profiles | **2 + 3** | L | M | Gear-train Remotion clip (ratio demonstration). |
| G7-ENG-002 | Energy Systems | Sankey-style energy-flow diagrams | **2** | M | M | Static Sankey. |
| G7-ENG-003 | Fluid Systems | Hydraulic-cylinder schematics, Pascal's-law diagram | **2** | L | M | Schematic SVG generator. |
| G7-ENG-004 | Structures Under Stress | Stress-strain plots, beam-failure diagrams | **2** | M | M | Static plots and SVGs. |

---

### Grade 8 — STEM (`grade8_stem.json`, 20 units)

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G8-MATH-001 | Linear Equations | Number-line, balance-scale steps | **2** | M | S | Reuse balance generator. |
| G8-MATH-002 | Functions and Linear Relationships | Slope-intercept plots, slope triangle | **2** | L | M | Plotly recipes for interactive web; static SVG fallback for mobile. |
| G8-MATH-003 | Systems of Linear Equations | Two-line plots with intersection | **2** | L | S | Static plot generator extension. |
| G8-MATH-004 | Exponents and Scientific Notation | Magnitude scale visualisation | **2** | M | S | Power-of-10 scale strip. |
| G8-MATH-005 | Transformations and Geometry | Pre-image / image with transformation arrows | **2 + 3** | L | M | Transformation Remotion (translate / reflect / rotate / dilate steps). |
| G8-MATH-006 | The Pythagorean Theorem | Right-triangle SVG, area-square decomposition | **2 + 3** | L | M | Classic Pythagoras-proof Remotion (square decomposition) is very high lift. |

#### Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G8-SCI-001 | Density and Buoyancy | Float / sink diagrams, displacement SVG | **2 + 3** | L | M | Buoyancy Remotion (object descending until it floats). |
| G8-SCI-002 | Waves: Light and Sound | Wave-superposition plots, EM-spectrum strip | **2 + 3** | L | M | Wave-superposition Remotion sets up G11-PHYS-010 + G12-PHYS-005. |
| G8-SCI-003 | Electricity and Magnetism | Circuit schematic, magnetic-field-line SVG | **2 + 3** | L | M | Reuse circuit generator from G6-ENG-002; field-line Remotion. |
| G8-SCI-004 | Evolution and Natural Selection | Phylogenetic-tree SVG, peppered-moth illustration | **2** | M | M | Static phylogenetic-tree generator. |
| G8-SCI-005 | Climate Change and Earth Systems | Carbon-cycle SVG, greenhouse-effect diagram | **2 + 3** | L | M | Greenhouse-effect Remotion (radiation in / heat trapped). |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G8-TECH-001 | Python: Data Structures | Visualised list / dict layout | **2** | M | S | SVG layout per data structure. |
| G8-TECH-002 | Python: File I/O and Exceptions | Try/except flowchart | **2** | S | S | Mermaid flowchart. |
| G8-TECH-003 | Web Technologies | DOM-tree SVG, request flow | **2** | M | S | Mermaid + SVG. |
| G8-TECH-004 | Binary and Number Systems | Binary-bit-grid SVG | **2** | M | S | Bit-grid generator. |
| G8-TECH-005 | Machine Learning Intro | Train / test split, simple decision tree | **2** | M | S | Static SVG. |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G8-ENG-001 | Mechanical Systems | Linkage diagrams, cam profiles | **2 + 3** | M | M | Cam-and-follower Remotion is striking. |
| G8-ENG-002 | Electrical Systems and Sensors | Sensor-actuator schematics, feedback-loop SVG | **2** | M | M | Reuse circuit generator. |
| G8-ENG-003 | CAD and 3D Design | Sketch / extrude / revolve example renders | **2** | M | M | Static SVG screen-mocks. |
| G8-ENG-004 | Automation and Robotics | Robot-architecture diagrams, sense-plan-act loop | **2** | M | S | Mermaid + SVG. |

---

### Grade 9 — STEM (`grade9_stem.json`, 19 units)

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G9-MATH-001 | Algebra: Polynomials | Algebra-tile factoring, polynomial-graph plots | **2** | M | M | Reuse algebra-tile generator from G6-MATH-003. |
| G9-MATH-002 | Quadratic Functions | Parabola plots with vertex, factored / standard form | **2** | L | M | Parabola plot generator with sliders (Plotly) on web. |
| G9-MATH-003 | Linear Systems and Inequalities | Shaded-region plots | **2** | L | S | Static SVGs. |
| G9-MATH-004 | Coordinate Geometry | Distance / midpoint diagrams | **2** | M | S | Coordinate-plane generator extension. |
| G9-MATH-005 | Introduction to Trigonometry | Right-triangle SVG, unit-circle | **2 + 3** | L | M | Unit-circle Remotion (sweep angle, sin / cos values trace). |

#### Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| **G9-SCI-001** | **Kinematics 1D** | x-t / v-t / a-t plots, motion-strip | **2 + 3** | L | M | **Highest priority outside G11 Sci** — same scaffolding as G11-PHYS-002 Kinematics; large G9 audience. |
| G9-SCI-002 | Newton's Laws of Motion | FBDs, action-reaction pairs | **2** | L | M | Reuse FBD generator. |
| G9-SCI-003 | Chemical Bonding | Lewis-dot diagrams, ionic / covalent illustrations | **2 + 3** | L | M | Lewis-dot SVG generator + bond-formation Remotion. |
| G9-SCI-004 | The Mole and Stoichiometry | Mole-ratio diagrams, balanced-equation visuals | **2** | M | M | Static SVG. |
| G9-SCI-005 | Cell Division and Growth | Mitosis / meiosis stage SVGs | **2 + 3** | L | L | Mitosis Remotion is the canonical biology animation; reuses cell-anatomy primitives. |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G9-TECH-001 | Object-Oriented Programming | Class / object diagrams | **2** | M | S | UML-light SVG. |
| G9-TECH-002 | Algorithms and Complexity | Big-O comparison plots, sort-step diagrams | **2 + 3** | L | M | Sort Remotion (bubble / insertion / merge) is high lift. |
| G9-TECH-003 | Relational Databases and SQL | ER diagrams, query-plan trees | **2** | M | S | Static ERDs. |
| G9-TECH-004 | Networking and Protocols | OSI layer diagram, packet route SVG | **2** | M | S | Layer-stack SVG. |
| G9-TECH-005 | Ethical AI and Society | Conceptual icons | **none** | S | S | Prose. |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G9-ENG-001 | Engineering Graphics and CAD | Orthographic-projection SVGs | **2** | L | M | First / third angle projection generator. |
| G9-ENG-002 | Materials Science | Stress-strain curves, microstructure SVG | **2** | M | M | Static. |
| G9-ENG-003 | Control Systems | Block diagrams, PID-response plots | **2 + 3** | L | M | PID-response Remotion (under / critical / overdamped) is striking. |
| G9-ENG-004 | Renewable Energy Systems | System-block diagrams (solar / wind / hydro) | **2** | M | M | Static SVGs. |

---

### Grade 10 — STEM (`grade10_stem.json`, 19 units)

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G10-MATH-001 | Functions: Domain, Range, Transformations | Function-family plots with transformation animation | **2 + 3** | L | M | Same recipe as G11-MATH-001 (already done); transformation Remotion. |
| G10-MATH-002 | Trigonometric Functions | Unit-circle, sine / cosine / tangent plots | **2 + 3** | L | M | Unit-circle Remotion (angle sweep traces sine wave). |
| G10-MATH-003 | Exponential and Logarithmic Functions | Growth / decay plots, log-scale demo | **2 + 3** | L | M | Log-scale-vs-linear Remotion is memorable. |
| G10-MATH-004 | Permutations, Combinations, Probability | Tree diagrams, Pascal's-triangle SVG | **2** | M | M | Pascal's-triangle generator. |
| G10-MATH-005 | Geometry: Circles and Proofs | Circle-theorem SVG (inscribed angles, tangent-chord) | **2** | L | M | One SVG per theorem. |

#### Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G10-SCI-001 | Energy: Work, Power, Efficiency | Work-energy-bar diagrams, force-displacement plots | **2** | M | M | Reuse energy-bar primitives from G6-SCI-002. |
| G10-SCI-002 | Waves and Optics | Reflection / refraction ray diagrams, lens diagrams | **2 + 3** | L | M | Refraction Remotion (light bending at interface) is canonical. |
| G10-SCI-003 | Thermodynamics | P-V diagrams, heat-flow direction arrows | **2** | M | M | Static P-V; reused in G11-PHYS-008 / G12-CHEM-003. |
| G10-SCI-004 | Organic Chemistry | Hydrocarbon skeletal structures, functional-group cards | **2** | L | L | Skeletal-structure SVG generator — heaviest chemistry-authoring effort; reused G11-CHEM-008/009, G12-CHEM-006/007/008. |
| G10-SCI-005 | Genetics and Biotechnology | DNA replication / transcription / translation diagrams | **2 + 3** | L | M | Central-dogma Remotion (DNA → mRNA → protein) reuses helix from G7-SCI-004. |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G10-TECH-001 | Data Science with Python | Sample histograms, scatter plots | **2** | M | S | Static plot examples. |
| G10-TECH-002 | Web Development | Page-layout sketches, request flow | **2** | M | S | Mermaid + SVG. |
| G10-TECH-003 | Computer Architecture | CPU / memory / cache diagram, fetch-decode-execute cycle | **2 + 3** | L | M | FDE-cycle Remotion. |
| G10-TECH-004 | Software Development Lifecycle | Workflow / Git-branching diagrams | **2** | M | S | Mermaid gitGraph. |
| G10-TECH-005 | Neural Networks Fundamentals | Perceptron / MLP architecture, backprop sketch | **2 + 3** | L | M | Backprop Remotion (gradient flowing back through layers). |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G10-ENG-001 | Statics and Structural Analysis | FBDs, truss-method diagrams | **2** | L | M | Reuse FBD generator. |
| G10-ENG-002 | Electrical Engineering Fundamentals | Circuit schematics, AC-waveform plots | **2 + 3** | L | M | Circuit + AC-phasor Remotion (rotating-vector representation). |
| G10-ENG-003 | Manufacturing Processes | Process-flow diagrams, machining SVGs | **2** | M | M | Static. |
| G10-ENG-004 | Engineering Ethics and Society | Case-study illustrations | **none** | S | S | Reading-driven. |

---

### Grade 11 — STEM (`grade11_stem.json`, 19 units, generic stream)

> The dedicated [`G11 Science deep-dive`](g11-science/visual_enhancement_plan.md) is the
> stream-specific (Physics / Chemistry / Biology) version. This is the
> **generic STEM** track, which uses subject buckets (Mathematics / Science /
> Technology / Engineering).

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-MATH-001 | Limits and Continuity | Zoom-in plots, ε-δ diagram | **2 + 3** | L | M | Limit Remotion (zoom into discontinuity) is the killer visual. |
| G11-MATH-002 | Derivatives: Rules and Applications | Tangent-line emergence, optimisation curves | **2 + 3** | L | M | Tangent-line Remotion as Δx → 0. |
| G11-MATH-003 | Integration: Antiderivatives and Area | Riemann sum → integral | **2 + 3** | L | M | Riemann-sum Remotion (rectangles → smooth curve). |
| G11-MATH-004 | Vectors and Matrices | 2D / 3D vector arrows, matrix-transformation | **2 + 3** | L | M | Matrix-transformation Remotion (basis vectors transformed). |
| G11-MATH-005 | Statistics: Inference and Regression | Distribution plots, regression line | **2** | M | S | Static plots. |

#### Science (generic — covers physics + chem + bio)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-SCI-001 | Dynamics: Forces in 2D | Projectile arc, FBDs in 2D | **2 + 3** | L | M | Reuse PHYS-002 Kinematics output directly. |
| G11-SCI-002 | Gravitation and Orbital Mechanics | Orbit ellipses, escape-velocity plot | **2 + 3** | L | M | Orbit Remotion (Kepler's 2nd law sweep). |
| G11-SCI-003 | Acids, Bases, Equilibrium | Titration curve, ICE-table diagrams | **2** | M | M | Plot generator. |
| G11-SCI-004 | Electrochemistry | Galvanic-cell schematic, electron-flow arrows | **2 + 3** | L | M | Electron-flow Remotion. |
| G11-SCI-005 | Evolution, Ecology, Conservation | Phylogenetic tree, predator-prey curves | **2** | M | M | Static. |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-TECH-001 | Advanced Python: Decorators and Generators | Wrapped-function diagram, generator-state SVG | **2** | M | S | SVG layout. |
| G11-TECH-002 | Computer Vision Basics | Convolution-kernel SVG, feature-map illustration | **2 + 3** | L | M | Convolution Remotion (kernel sliding over image). |
| G11-TECH-003 | Cloud Computing | Architecture diagrams, container layouts | **2** | M | S | Mermaid + SVG. |
| G11-TECH-004 | Cryptography | Block-cipher diagrams, PKI flow | **2** | M | M | Static SVGs. |
| G11-TECH-005 | Natural Language Processing | Embedding-space SVG, attention-pattern grid | **2 + 3** | L | M | Attention-pattern Remotion is high lift. |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-ENG-001 | Fluid Mechanics | Streamline diagrams, Bernoulli pressure plot | **2 + 3** | L | M | Streamline Remotion. |
| G11-ENG-002 | Signal Processing | Time-domain / frequency-domain plots | **2 + 3** | L | M | FFT Remotion (time → frequency). |
| G11-ENG-003 | Embedded Systems | Microcontroller pinout, sensor / actuator schematics | **2** | M | M | Reuse circuit generator. |
| G11-ENG-004 | Systems Engineering | Block diagrams, V-model | **2** | M | S | Mermaid. |

---

### Grade 12 — STEM (`grade12_stem.json`, 19 units, generic stream)

#### Mathematics

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-MATH-001 | Advanced Calculus: Techniques of Integration | Step-by-step substitution, integration-by-parts table | **2** | M | M | Static SVG. |
| G12-MATH-002 | Differential Equations | Slope fields, solution-curve plots | **2 + 3** | L | M | Slope-field Remotion (vector flow). |
| G12-MATH-003 | Multivariable Calculus | 3D surface plots, gradient-vector field | **2 + 3** | L | L | 3D surface + gradient Remotion. |
| G12-MATH-004 | Linear Algebra | Eigenvector arrows, transformation grid | **2 + 3** | L | M | Eigenvector Remotion (basis reshape). |
| G12-MATH-005 | Discrete Mathematics | Graph diagrams, induction visuals | **2** | M | M | Graph-theory SVG generator. |

#### Science (generic)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-SCI-001 | Momentum, Impulse, Collisions | Vector arrows, before / after diagrams | **2 + 3** | L | M | Collision Remotion (elastic / inelastic). |
| G12-SCI-002 | Quantum Mechanics | Wavefunction plots, particle-in-box | **2 + 3** | L | M | Wavefunction Remotion (probability density evolving). |
| G12-SCI-003 | Nuclear Physics and Radioactivity | Decay-chain diagrams, half-life plots | **2 + 3** | L | M | Half-life Remotion (sample atoms decaying). |
| G12-SCI-004 | Biochemistry | Enzyme-substrate fit, metabolic-pathway SVG | **2 + 3** | L | M | Enzyme-binding Remotion. |
| G12-SCI-005 | Astrophysics | Stellar-evolution flowchart, HR diagram | **2 + 3** | L | M | Stellar-evolution Remotion. |

#### Technology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-TECH-001 | Machine Learning in Practice | Pipeline diagram, validation-curve plots | **2** | M | S | Static SVG. |
| G12-TECH-002 | Deep Learning and Neural Networks | CNN / RNN / transformer architecture diagrams | **2 + 3** | L | M | Attention-pattern Remotion. |
| G12-TECH-003 | Distributed Systems | Architecture diagrams, consensus-protocol flow | **2** | M | M | Mermaid + SVG. |
| G12-TECH-004 | Quantum Computing | Bloch sphere, circuit diagrams | **2 + 3** | L | L | Bloch-sphere Remotion (rotation under gate). |
| G12-TECH-005 | Capstone: Applied AI | Project diagrams | **2** | S | S | Per-project. |

#### Engineering

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-ENG-001 | Advanced Robotics | SLAM map, planning-tree SVG | **2 + 3** | L | M | Path-planning Remotion. |
| G12-ENG-002 | Aerospace Engineering | Airfoil cross-section, lift-drag plots | **2 + 3** | L | M | Airfoil Remotion (flow over wing). |
| G12-ENG-003 | Biomedical Engineering | Device schematics | **2** | M | M | Static SVG. |
| G12-ENG-004 | Capstone Engineering Design | Project-flow diagrams | **2** | S | S | Per-project. |

---

### Grade 12 — Science Stream (`grade12_science.json`, 28 units)

> CBSE-aligned stream, sister curriculum to G11-Science. Heavy physics +
> chemistry visual lift. Roughly the same recipe as
> [`g11-science/visual_enhancement_plan.md`](g11-science/visual_enhancement_plan.md).

#### Physics (8 units)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-PHYS-001 | Electrostatics | Field-line SVG, capacitor schematics | **2 + 3** | L | M | Field-line Remotion (charge configurations). |
| **G12-PHYS-002** | **Current Electricity** | Circuit schematics, Wheatstone bridge | **2** | L | L | Reuse + extend circuit-schematic generator (G6-ENG-002 lineage). Foundational. |
| G12-PHYS-003 | Magnetic Effects and EM Induction | Magnetic-field-line SVG, AC-waveform | **2 + 3** | L | M | EM-induction Remotion (flux change → induced current). |
| G12-PHYS-004 | Electromagnetic Waves | EM-spectrum strip, transverse-wave SVG | **2 + 3** | L | M | EM-wave Remotion (E and B fields oscillating perpendicular). |
| G12-PHYS-005 | Optics | Ray diagrams, interference patterns, diffraction | **2 + 3** | L | L | **High lift** — ray-diagram generator + interference-pattern Remotion. Reuse to G10-SCI-002, G8-SCI-002. |
| G12-PHYS-006 | Dual Nature of Radiation and Matter | Photoelectric-effect diagram, de Broglie wave | **2 + 3** | L | M | Photoelectric Remotion (photon → electron ejection). |
| G12-PHYS-007 | Atoms and Nuclei | Bohr-model diagram, decay-chain | **2 + 3** | L | M | Bohr Remotion (electron transition emits photon). |
| G12-PHYS-008 | Electronic Devices | p-n junction SVG, transistor schematics, logic gates | **2 + 3** | L | M | Junction Remotion (electron / hole flow under bias). |

#### Chemistry (10 units)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-CHEM-001 | Solutions | Phase diagrams, Raoult-law plots | **2** | M | M | Static plots. |
| **G12-CHEM-002** | **Electrochemistry** | Galvanic cell SVG, Nernst plot | **2 + 3** | L | M | Cell schematic + electron-flow Remotion. |
| G12-CHEM-003 | Chemical Kinetics | Arrhenius plot, energy profile | **2 + 3** | L | M | Energy-profile Remotion (transition-state arc). |
| G12-CHEM-004 | d- and f-Block Elements | Periodic-trend heatmap, electron-config diagrams | **2** | M | M | Reuse heatmap from G7-SCI-001 / G11-CHEM-003. |
| G12-CHEM-005 | Coordination Compounds | Octahedral / tetrahedral geometry SVG, crystal-field splitting | **2 + 3** | L | M | Geometry-rotate Remotion. |
| G12-CHEM-006 | Haloalkanes and Haloarenes | Skeletal structures, SN1 / SN2 mechanism arrows | **2 + 3** | L | L | Mechanism-arrow Remotion (curved arrows showing electron movement). Reuse skeletal generator. |
| G12-CHEM-007 | Alcohols, Phenols and Ethers | Skeletal structures, mechanism arrows | **2** | L | L | Reuse generators. |
| G12-CHEM-008 | Aldehydes, Ketones and Carboxylic Acids | Skeletal + nucleophilic-addition mechanism | **2 + 3** | L | L | Mechanism Remotion. |
| G12-CHEM-009 | Amines | Skeletal structures, diazonium reactions | **2** | M | M | Reuse generators. |
| G12-CHEM-010 | Biomolecules | Protein / DNA / carbohydrate structures | **2** | L | L | Biomolecule SVG library; reuse helix from G7-SCI-004. |

#### Mathematics (6 units)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-MATH-001 | Relations and Functions | Arrow diagrams, inverse-trig plots | **2** | L | M | Reuse arrow-diagram generator from G11-MATH-001. |
| G12-MATH-002 | Algebra (Matrices, Determinants) | Matrix-as-grid SVG | **2** | M | S | Static. |
| G12-MATH-003 | Calculus (heavy unit) | Slope fields, Riemann sums, applications plots | **2 + 3** | L | L | Reuse multiple Remotion clips: tangent line, area-under-curve, slope field. |
| G12-MATH-004 | Vectors and 3D Geometry | 3D vector arrows, line / plane SVG | **2 + 3** | L | M | 3D Remotion (camera rotation around configuration). |
| G12-MATH-005 | Linear Programming | Feasible-region plots, vertex evaluation | **2** | M | S | Static. |
| G12-MATH-006 | Probability | Tree diagrams, distribution plots | **2** | M | S | Mermaid + plots. |

#### Biology (4 units)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-BIO-001 | Sexual Reproduction | Reproductive-anatomy SVGs (plant, animal), fertilisation flow | **2 + 3** | L | L | Fertilisation Remotion. Reuse cell-anatomy primitives. |
| G12-BIO-002 | Genetics and Evolution | Punnett squares, linkage maps, phylogenetic tree | **2 + 3** | L | L | Reuse from G7-SCI-004 + G8-SCI-004. |
| G12-BIO-003 | Biology and Human Welfare | Disease-cycle diagrams, microbe SVGs | **2** | M | M | Static SVGs. |
| G12-BIO-004 | Ecology and Environment | Ecosystem-pyramid SVG, nutrient-cycle diagrams | **2** | L | M | Reuse cycle generators from G6-SCI-005. |

---

### Grade 11 — Commerce (`grade11_commerce.json`, 6 units)

> Heavy on tables, statements, and process flows. Almost entirely Option 2; no
> Remotion clips earn their cost in foundational accountancy / business
> studies / economics.

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-ACC-001 | Theoretical Framework | Accounting-cycle flowchart | **2** | M | S | Mermaid cycle. |
| G11-ACC-002 | Financial Statements | Trial-balance / P&L / balance-sheet templates | **2** | L | M | **Foundational templates** — reuse for G12-ACC-* and the Commerce stream. |
| G11-BUS-001 | Nature and Purpose of Business | Org-form comparison tables | **2** | M | S | Markdown tables. |
| G11-BUS-002 | Finance and Trade | Source-of-finance flowchart | **2** | M | S | Mermaid. |
| G11-ECON-001 | Statistics for Economics | Histogram, mean / median / mode plots | **2** | M | M | Reuse plot generators. |
| G11-ECON-002 | Indian Economic Development | Timeline diagrams, sector composition | **2** | M | M | Static SVG. |

---

### Grade 12 — Commerce (`grade12_commerce.json`, 7 units)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-ACC-001 | Partnership Accounts | Capital-account / current-account ledgers | **2** | M | M | Tables. |
| G12-ACC-002 | Company Accounts | Share-capital tables, debenture schedules | **2** | M | M | Tables. |
| G12-ACC-003 | Financial Statement Analysis | Cash-flow Sankey, ratio-comparison plots | **2** | L | M | Cash-flow Sankey is high lift. |
| G12-BUS-001 | Principles and Functions of Management | POSDCORB diagram | **2** | S | S | Single SVG. |
| G12-BUS-002 | Business Finance and Marketing | 4Ps diagram, capital-budgeting tables | **2** | M | S | Mermaid + tables. |
| G12-ECON-001 | Introductory Macroeconomics | Aggregate-demand / supply plots, Lorenz curve | **2** | L | M | Plot generator. |
| G12-ECON-002 | Indian Economic Development | Timeline, sector charts | **2** | M | M | Reuse from G11-ECON-002. |

---

### Grade 11 — English (`grade11_english.json`, 3 units) & Grade 12 — English (`grade12_english.json`, 3 units)

> English Core is text-driven by definition. Visuals add little beyond
> stock illustrations for literature passages.

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-ENG-001, G12-ENG-001 | Reading Skills | None-needed | **none** | S | S | Skip. |
| G11-ENG-002, G12-ENG-002 | Writing Skills | Format templates (notice / letter / report) | **2** | M | S | Static template SVG / formatted markdown. |
| G11-ENG-003, G12-ENG-003 | Literature | Optional thematic illustrations | **none** | S | S | Skip — literature is best left to the prose. |

---

### Grade 11 — Humanities (`grade11_humanities.json`, 9 units)

> Humanities visuals are timelines, maps, comparison tables, and conceptual
> diagrams. Animation rarely earns its cost.

#### History

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-HIST-001 | Early Societies | Timeline + region maps | **2** | M | M | Map / timeline SVG generator. |
| G11-HIST-002 | Empires | Empire-extent maps, dynasty timelines | **2** | M | M | Same generator. |
| G11-HIST-003 | Changing Traditions | Industrial-revolution timeline, comparison tables | **2** | M | M | Same. |

#### Political Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-POL-001 | Indian Constitution at Work | Branches-of-government diagram, federal-structure | **2** | M | S | Static SVG. |
| G11-POL-002 | Political Theory | Conceptual maps | **2** | S | S | Mermaid. |

#### Geography

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-GEO-001 | Fundamentals of Physical Geography | Earth cross-section, climate-zone maps, water cycle | **2 + 3** | L | M | Water-cycle Remotion (reuses G5-SCI-005 generator). Plate-tectonics Remotion (reuses G6-SCI-003). |
| G11-GEO-002 | India – Physical Environment | India physical map, drainage / soil layers | **2** | L | M | Annotated SVG of India. |

#### Psychology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G11-PSY-001 | Introduction | Methods-of-enquiry flowchart | **2** | S | S | Mermaid. |
| G11-PSY-002 | Biological and Cultural Shaping | Brain-anatomy SVG, neuron diagram, learning-curve plots | **2 + 3** | L | M | Brain-region SVG; neural-firing Remotion. |

---

### Grade 12 — Humanities (`grade12_humanities.json`, 9 units)

#### History

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-HIST-001 | Early India | Indus-valley map, Harappan-site SVG | **2** | M | M | Same map / timeline generator. |
| G12-HIST-002 | Medieval India | Bhakti / Sufi tradition timeline, Mughal-empire map | **2** | M | M | Same. |
| G12-HIST-003 | Modern India | Colonial-era timelines, partition map, freedom-struggle | **2** | M | M | Same. |

#### Political Science

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-POL-001 | Contemporary World Politics | World-map overlays (Cold-war blocks, US-hegemony era) | **2** | M | M | Map generator. |
| G12-POL-002 | Politics in India since Independence | Election-result timelines, party-system diagrams | **2** | M | S | Static. |

#### Geography

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-GEO-001 | Fundamentals of Human Geography | Population-pyramid SVGs, migration-flow maps | **2** | L | M | Pyramid generator. |
| G12-GEO-002 | India – People and Economy | Population-density maps, agriculture overlays | **2** | L | M | Reuse India-map from G11-GEO-002. |

#### Sociology

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G12-SOC-001 | Indian Society | Caste / community structure diagrams | **2** | S | S | Mermaid + tables. |
| G12-SOC-002 | Social Change and Development | Globalisation flow diagrams | **2** | S | S | Mermaid. |

---

### Grade 9 — English / Advanced (`grade9_english.json`, `grade9_advanced.json`)

| Unit | Title | Visual primitives | Option | Lift | Effort | Note |
|---|---|---|---|---|---|---|
| G9-ENG-001 (English) | Unit 1 | (placeholder content) | **none** | S | S | Curriculum stub — revisit when content is authored. |
| G9-ENG-001 (Advanced) | Unit 1 | (placeholder content) | **none** | S | S | Same. |

---

## Cross-curriculum reusable generators (by impact)

A handful of TS spec generators are reused across many units. Investing in
these first compounds across the catalogue.

| Generator | Initial unit | Re-used in |
|---|---|---|
| **Coordinate-plane SVG** | G6-MATH-002 | every plot in G6 / G7 / G8 / G9 / G10 / G11 / G12 math + physics + econ |
| **FBD / arrow-diagram** | G11-PHYS-002 (done) | G5-SCI-002, G9-SCI-002, G10-ENG-001, G11-SCI-001, etc. |
| **Circuit-schematic** | G6-ENG-002 | G8-SCI-003, G10-ENG-002, G11-ENG-003, G12-PHYS-002 + 008 |
| **Cell / anatomy** | G6-SCI-001 | G7-SCI-003, G9-SCI-005, G12-BIO-001..004 |
| **Skeletal-structure (organic)** | G10-SCI-004 | G11-CHEM-008/009, G12-CHEM-006/007/008/009 |
| **Periodic-trend heatmap** | G7-SCI-001 | G11-CHEM-003, G12-CHEM-004 |
| **Wave / superposition** | G8-SCI-002 | G11-PHYS-010, G12-PHYS-004/005 |
| **Phylogenetic / Punnett** | G7-SCI-004, G8-SCI-004 | G11-SCI-005, G12-BIO-002 |
| **Map / timeline** | G11-GEO-001 | every history + geography unit |
| **Plotly slider plot** | G8-MATH-002 | every Mathematics unit G8+ |
| **Cycle (Mermaid + Remotion)** | G6-SCI-005 | G8-SCI-005, G11-BIO-005, G12-BIO-004 |

If we ship 3-4 generators well, ~70% of all 218 units land cheaply on top of
them.

---

## Recommended build order (next 10 hand-authored units)

After the two reference exemplars (G11-MATH-001, G11-PHYS-002), invest the
next 10 units of effort in these — chosen for the **maximum reuse of
generators** and **largest student-audience coverage**.

| # | Unit | Builds (reusable) | Audience |
|---|---|---|---|
| 1 | **G11-PHYS-010** Oscillations & Waves | Wave-superposition Remotion, SHM clip | G11 Sci, downstream G12 Phys |
| 2 | **G9-SCI-001** Kinematics 1D | x-t / v-t / a-t plot generator (reuse from G11-PHYS-002) | every G9 student |
| 3 | **G11-CHEM-002** Structure of Atom | Bohr-shell SVG, orbital shapes | G11 Sci + G12 |
| 4 | **G6-SCI-001** Cells | Cell-anatomy SVG generator | G6 + 4 downstream units |
| 5 | **G6-ENG-002** Electronics Basics | Circuit-schematic generator | 6+ downstream units |
| 6 | **G7-SCI-001** Atoms & Periodic Table | Periodic-trend heatmap generator | G7 + G11/G12 chem |
| 7 | **G10-SCI-004** Organic Chemistry | Skeletal-structure generator | G11/G12 organic chem |
| 8 | **G11-MATH-002** Derivatives | Tangent-line Remotion | G11 + G12 math |
| 9 | **G8-SCI-002** Waves: Light & Sound | Wave-superposition primitives | G11-PHYS-010, G12-PHYS-005 |
| 10 | **G12-PHYS-005** Optics | Ray-diagram generator, interference Remotion | G10-SCI-002, G8-SCI-002 |

After these 10 units, we will have built **9 reusable generators** that
collectively cover ~70 % of all 218 units' visual needs. That's the corpus
the automation in #320 needs as input — patterns extracted from real human
work.

---

## What this audit feeds

- **Phase C** (library expansion) — pick from the build-order list above
- **Phase B** (#320 code-gen automation) — the per-unit MEMO.md captured
  during hand-authoring becomes the spec for which templates the LLM
  generates from
- **Coverage tracking** — 218 units total, 2 done (~1%). After build-order
  sequence: 12 done (~6%) but with the 9 reusable generators, on-paper
  coverage shoots higher because everything math / chem / physics / circuit /
  anatomy in subsequent units fits the pre-built scaffolding

---

*Audit author: broker. Generated 2026-05-07 from `data/grade*.json` (218
canonical units, CBSE duplicates excluded). Recommendations are based on
domain knowledge of curricular topics; per-unit assessments should be
revisited once the authoring lands and the MEMO.md captures real-world
edge cases.*
