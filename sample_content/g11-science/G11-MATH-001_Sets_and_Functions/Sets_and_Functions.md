# Sets and Functions

> Unit `G11-MATH-001`
> Reading level: Grade 11–12 (university-preparatory)
> Estimated duration: 45 min

## Synopsis

This lesson introduces the foundational language of modern mathematics: **sets** and **functions**. Beginning with rigorous set-builder notation and progressing through function definitions, domain-and-range analysis, and composition of functions, students will develop the abstract reasoning skills essential for calculus, linear algebra, and beyond. By the end of this lesson, you will be able to manipulate sets algebraically, classify functions by their properties, and evaluate composite and inverse functions with confidence.

## Key Concepts

- **Set notation and set-builder notation** — representing collections using $\{x \mid P(x)\}$ and roster form
- **Set operations** — union $A \cup B$, intersection $A \cap B$, difference $A \setminus B$, and complement $A^c$
- **Cartesian product** — forming ordered pairs $A \times B = \{(a,b) \mid a \in A,\, b \in B\}$
- **Relations and functions** — a function $f: A \to B$ as a special relation where every element of the domain maps to exactly one element of the codomain
- **Domain, codomain, and range** — distinguishing $\text{dom}(f)$, $\text{codom}(f)$, and $\text{ran}(f) \subseteq \text{codom}(f)$
- **Injectivity, surjectivity, and bijectivity** — one-to-one, onto, and one-to-one correspondence
- **Composition of functions** — $(f \circ g)(x) = f(g(x))$ and its domain restrictions
- **Inverse functions** — conditions for $f^{-1}$ to exist and the identity $f(f^{-1}(x)) = x$

## Learning Objectives

- **Explain** the distinction between a set, a relation, and a function using precise mathematical language, and represent each using appropriate notation including set-builder form and arrow diagrams.
- **Identify** whether a given function is injective, surjective, or bijective by applying the formal definitions and, where applicable, the horizontal line test.
- **Calculate** the domain and range of algebraic, radical, and rational functions, expressing answers in interval notation and set notation.
- **Evaluate and simplify** composite functions $(f \circ g)(x)$ and $(g \circ f)(x)$, determining the restricted domain of the composition when necessary.
- **Derive** the inverse of a bijective function algebraically and verify the result using the composition identity $f^{-1}(f(x)) = x$.

---

# Sets and Functions: From Foundational Theory to Functional Reasoning

## Set Theory: Definitions, Notation, and Fundamental Operations

## 1.1 What Is a Set?

A **set** is a well-defined collection of distinct objects, called **elements** or **members**. The concept of a set is foundational to virtually all of modern mathematics.

> Mathematics is the language in which God has written the universe.
> — Galileo Galilei

We denote sets with capital letters ($A$, $B$, $S$, etc.) and their elements with lowercase letters. Membership is expressed as:

- $x \in A$ means "$x$ is an element of $A$"
- $x \notin A$ means "$x$ is not an element of $A$"

### 1.2 Ways to Define a Set

| Method | Notation | Example |
|:-------|:---------|:--------|
| Roster (Enumeration) | List all elements | $A = \{1, 2, 3, 4\}$ |
| Set-Builder | Describe with a rule | $B = \{x \mid x \in \mathbb{Z},\; 1 \leq x \leq 4\}$ |
| Descriptive | Words | "The set of all even natural numbers" |

### 1.3 Special Sets

| Symbol | Name | Description |
|:------:|:-----|:------------|
| $\emptyset$ or $\{\}$ | Empty Set | Contains no elements |
| $\mathbb{N}$ | Natural Numbers | $\{1, 2, 3, \ldots\}$ |
| $\mathbb{Z}$ | Integers | $\{\ldots, -2, -1, 0, 1, 2, \ldots\}$ |
| $\mathbb{Q}$ | Rational Numbers | $\left\{\dfrac{p}{q} \mid p, q \in \mathbb{Z},\; q \neq 0\right\}$ |
| $\mathbb{R}$ | Real Numbers | All points on the number line |
| $\mathbb{U}$ | Universal Set | The set of all objects under consideration |

### 1.4 Subsets and Power Sets

Set $A$ is a **subset** of $B$, written $A \subseteq B$, if every element of $A$ is also an element of $B$:

$$A \subseteq B \iff \forall x,\; (x \in A \Rightarrow x \in B)$$

Two sets are **equal** if and only if they are subsets of each other:

$$A = B \iff (A \subseteq B) \land (B \subseteq A)$$

The **power set** of $A$, denoted $\mathcal{P}(A)$, is the set of all subsets of $A$. If $|A| = n$ (where $|A|$ denotes the **cardinality**, or number of elements, of $A$), then:

$$|\mathcal{P}(A)| = 2^n$$

### 1.5 Set Operations

Let $A$ and $B$ be subsets of a universal set $\mathbb{U}$.

| Operation | Symbol | Definition |
|:----------|:------:|:-----------|
| Union | $A \cup B$ | $\{x \mid x \in A \text{ or } x \in B\}$ |
| Intersection | $A \cap B$ | $\{x \mid x \in A \text{ and } x \in B\}$ |
| Difference | $A \setminus B$ | $\{x \mid x \in A \text{ and } x \notin B\}$ |
| Complement | $A'$ or $A^c$ | $\{x \in \mathbb{U} \mid x \notin A\}$ |
| Symmetric Difference | $A \triangle B$ | $(A \setminus B) \cup (B \setminus A)$ |

### 1.6 Key Properties (Laws of Set Algebra)

$$A \cup (B \cap C) = (A \cup B) \cap (A \cup C) \quad \text{(Distributive Law)}$$

$$\overline{A \cup B} = \overline{A} \cap \overline{B} \quad \text{(De Morgan's First Law)}$$

$$\overline{A \cap B} = \overline{A} \cup \overline{B} \quad \text{(De Morgan's Second Law)}$$

## Worked Example 1: Set Operations

**Given:** $\mathbb{U} = \{1, 2, 3, 4, 5, 6, 7, 8\}$, $A = \{1, 2, 3, 4\}$, $B = \{3, 4, 5, 6\}$.

Find: **(a)** $A \cup B$, **(b)** $A \cap B$, **(c)** $A \setminus B$, **(d)** $A'$.

**Solution:**

1. **Union** — combine all elements, no duplicates:

$$A \cup B = \{1, 2, 3, 4, 5, 6\}$$

2. **Intersection** — elements common to both:

$$A \cap B = \{3, 4\}$$

3. **Set Difference** — elements in $A$ but not in $B$:

$$A \setminus B = \{1, 2\}$$

4. **Complement of $A$** — elements in $\mathbb{U}$ not in $A$:

$$A' = \{5, 6, 7, 8\}$$

## Worked Example 2: Power Sets and Cardinality

**Given:** $S = \{a, b, c\}$.

Find $\mathcal{P}(S)$ and verify $|\mathcal{P}(S)| = 2^{|S|}$.

**Solution:**

1. The cardinality is $|S| = 3$, so we expect $2^3 = 8$ subsets.

2. List all subsets systematically by size:

$$\mathcal{P}(S) = \bigl\{\emptyset,\; \{a\},\; \{b\},\; \{c\},\; \{a,b\},\; \{a,c\},\; \{b,c\},\; \{a,b,c\}\bigr\}$$

3. Count: there are indeed **8** elements in $\mathcal{P}(S)$, confirming:

$$|\mathcal{P}(S)| = 2^3 = 8 \checkmark$$

**Note:** The empty set $\emptyset$ is always a subset of every set, and every set is a subset of itself.

### Practice Question

Let $\mathbb{U} = \{x \in \mathbb{Z} \mid 1 \leq x \leq 10\}$, $P = \{2, 4, 6, 8, 10\}$ (even integers), and $Q = \{1, 2, 3, 5, 7\}$ (contains 1 and the first four primes).

**(a)** Find $P \cup Q$, $P \cap Q$, and $P \setminus Q$.
**(b)** Verify De Morgan's First Law: show that $\overline{P \cup Q} = \overline{P} \cap \overline{Q}$ by computing each side independently.
**(c)** Write $P$ in set-builder notation.


## Relations and the Concept of a Function

## 2.1 Ordered Pairs and the Cartesian Product

An **ordered pair** $(a, b)$ is a pair of elements where order matters: $(a, b) \neq (b, a)$ unless $a = b$. The **Cartesian product** of sets $A$ and $B$ is:

$$A \times B = \{(a, b) \mid a \in A,\; b \in B\}$$

If $|A| = m$ and $|B| = n$, then $|A \times B| = mn$.

## 2.2 Relations

A **binary relation** $R$ from $A$ to $B$ is any subset of the Cartesian product:

$$R \subseteq A \times B$$

We write $a\,R\,b$ to mean $(a, b) \in R$. The **domain** of $R$ is the set of all first components, and the **range** (or image) is the set of all second components that actually appear.

## 2.3 Definition of a Function

A **function** (or **mapping**) $f$ from set $A$ to set $B$, written

$$f: A \to B$$

is a relation in which **every element of $A$ is paired with exactly one element of $B$**. Formally:

$$\forall x \in A,\; \exists! y \in B \text{ such that } (x, y) \in f$$

Here:
- $A$ is the **domain** of $f$, denoted $\text{dom}(f)$
- $B$ is the **codomain** of $f$
- The **range** (or **image**) of $f$ is $\text{ran}(f) = \{f(x) \mid x \in A\} \subseteq B$

> The art of doing mathematics consists in finding that special case which contains all the germs of generality.
> — David Hilbert

## 2.4 The Vertical Line Test

For a relation defined by a graph in the Cartesian plane, it represents a function if and only if **every vertical line intersects the graph at most once**. This enforces the single-output requirement.

## 2.5 Injective, Surjective, and Bijective Functions

| Property | Definition | Informal Meaning |
|:---------|:-----------|:-----------------|
| **Injective** (one-to-one) | $f(a) = f(b) \Rightarrow a = b$ | No two inputs share the same output |
| **Surjective** (onto) | $\forall y \in B,\; \exists x \in A : f(x) = y$ | Every element of the codomain is an output |
| **Bijective** (one-to-one correspondence) | Both injective and surjective | Perfect pairing between domain and codomain |

Only **bijective** functions have a well-defined **inverse function** $f^{-1}: B \to A$.

## 2.6 Equal Functions

Two functions $f$ and $g$ are **equal** if and only if:
1. They have the same domain, $\text{dom}(f) = \text{dom}(g)$.
2. $f(x) = g(x)$ for every $x$ in that common domain.

## Worked Example 1: Identifying Functions from Arrow Diagrams

Decide whether each of the following mappings from $A = \{1, 2, 3\}$ to $B = \{p, q, r\}$ is a function.

| Mapping | Pairs | Function? | Reason |
|:--------|:------|:---------:|:-------|
| $R_1$ | $(1,p),(2,q),(3,r)$ | ✓ Yes | Each element of $A$ maps to exactly one element of $B$ |
| $R_2$ | $(1,p),(1,q),(2,r)$ | ✗ No | Element $1$ maps to two outputs: $p$ and $q$ |
| $R_3$ | $(1,p),(2,p),(3,q)$ | ✓ Yes | Repetition of outputs is allowed; each input has exactly one output |
| $R_4$ | $(1,p),(2,q)$ | ✗ No | Element $3 \in A$ has no output (undefined) |

**Key Insight:** $R_3$ is a valid function — it is **not** injective (since $f(1)=f(2)=p$), but it satisfies the definition of a function.

## Worked Example 2: Finding Domain, Codomain, and Range

**Given:** $f: \mathbb{R} \to \mathbb{R}$ defined by $f(x) = x^2 - 4$.

**Find the domain, codomain, and range.**

**Solution:**

1. **Domain:** The expression $x^2 - 4$ is defined for all real $x$, so:

$$\text{dom}(f) = \mathbb{R} = (-\infty, +\infty)$$

2. **Codomain:** As declared in the mapping notation, the codomain is $\mathbb{R}$.

3. **Range:** Since $x^2 \geq 0$ for all $x \in \mathbb{R}$, the minimum value of $f(x)$ occurs at $x = 0$:

$$f(0) = 0 - 4 = -4$$

As $|x| \to \infty$, $f(x) \to +\infty$. Therefore:

$$\text{ran}(f) = [-4, +\infty)$$

Note that $\text{ran}(f) \subsetneq \mathbb{R}$, confirming that $f$ is **not surjective** as a function into $\mathbb{R}$.

### Practice Question

Consider the relation $R = \{(x, y) \mid y^2 = x,\; x \in [0, 9],\; x \in \mathbb{R}\}$.

**(a)** Is $R$ a function from $\mathbb{R}$ to $\mathbb{R}$? Justify your answer rigorously using the definition of a function.

**(b)** If $R$ is **not** a function, suggest a minimal restriction on the codomain variable $y$ that would make the modified relation a function, and state its domain and range.

**(c)** Is the function you described in (b) injective, surjective (with codomain $\mathbb{R}$), or bijective? Justify each claim.


## Types of Functions and Their Graphs

## 3.1 Classification of Functions

Functions can be classified by their algebraic form. Understanding each type — its shape, key features, and behaviour — is critical for modelling and analysis.

### 3.2 Polynomial Functions

A **polynomial function** of degree $n$ has the form:

$$f(x) = a_n x^n + a_{n-1}x^{n-1} + \cdots + a_1 x + a_0, \quad a_n \neq 0$$

| Degree | Name | General Form | Example |
|-------:|:-----|:-------------|:--------|
| 0 | Constant | $f(x) = c$ | $f(x) = 5$ |
| 1 | Linear | $f(x) = mx + b$ | $f(x) = 2x - 3$ |
| 2 | Quadratic | $f(x) = ax^2 + bx + c$ | $f(x) = x^2 - 4x + 3$ |
| 3 | Cubic | $f(x) = ax^3 + \cdots$ | $f(x) = x^3 - x$ |
| $n$ | Degree-$n$ polynomial | — | — |

### 3.3 Rational Functions

A **rational function** is the ratio of two polynomials:

$$f(x) = \frac{P(x)}{Q(x)}, \quad Q(x) \neq 0$$

The domain excludes all $x$ for which $Q(x) = 0$. Vertical asymptotes occur at these excluded values (when $P(x) \neq 0$ there).

### 3.4 Absolute Value Function

$$f(x) = |x| = \begin{cases} x & \text{if } x \geq 0 \\ -x & \text{if } x < 0 \end{cases}$$

Domain: $\mathbb{R}$; Range: $[0, +\infty)$.

### 3.5 Piecewise-Defined Functions

A **piecewise function** uses different rules for different parts of the domain. Example:

$$g(x) = \begin{cases} x^2 & \text{if } x < 0 \\ 2x + 1 & \text{if } 0 \leq x \leq 3 \\ 10 - x & \text{if } x > 3 \end{cases}$$

### 3.6 Evaluating Piecewise Functions — Value Table

For the function $g$ above:

| $x$ | Applicable Rule | $g(x)$ |
|----:|:----------------|-------:|
| $-3$ | $x^2$ | $9$ |
| $-1$ | $x^2$ | $1$ |
| $0$ | $2x+1$ | $1$ |
| $2$ | $2x+1$ | $5$ |
| $3$ | $2x+1$ | $7$ |
| $5$ | $10 - x$ | $5$ |

### 3.7 Even and Odd Functions

| Property | Condition | Geometric Interpretation |
|:---------|:----------|:------------------------|
| **Even** | $f(-x) = f(x)$ for all $x$ | Symmetric about the $y$-axis |
| **Odd** | $f(-x) = -f(x)$ for all $x$ | Symmetric about the origin |
| **Neither** | Neither condition holds | No such symmetry |

## Worked Example 1: Domain of a Rational Function

**Find the domain of** $f(x) = \dfrac{3x + 1}{x^2 - 5x + 6}$.

**Solution:**

1. Factor the denominator:

$$x^2 - 5x + 6 = (x - 2)(x - 3)$$

2. The denominator equals zero when $x = 2$ or $x = 3$. These must be excluded from the domain.

3. Therefore:

$$\text{dom}(f) = \mathbb{R} \setminus \{2, 3\} = (-\infty, 2) \cup (2, 3) \cup (3, +\infty)$$

## Worked Example 2: Classifying a Function as Even, Odd, or Neither

**Determine whether each function is even, odd, or neither.**

**(a)** $h(x) = 4x^4 - 2x^2 + 1$

**(b)** $k(x) = 3x^3 - x$

**(c)** $p(x) = x^2 + x$

**Solution for (a):**

1. Substitute $-x$ for $x$:

$$h(-x) = 4(-x)^4 - 2(-x)^2 + 1 = 4x^4 - 2x^2 + 1$$

2. Compare: $h(-x) = h(x)$. Therefore $h$ is **even**.

**Solution for (b):**

1. Substitute $-x$:

$$k(-x) = 3(-x)^3 - (-x) = -3x^3 + x = -(3x^3 - x) = -k(x)$$

2. Since $k(-x) = -k(x)$, $k$ is **odd**.

**Solution for (c):**

1. Substitute $-x$:

$$p(-x) = (-x)^2 + (-x) = x^2 - x$$

2. Check even: $p(-x) = x^2 - x \neq x^2 + x = p(x)$ (unless $x=0$). ✗
3. Check odd: $-p(x) = -(x^2+x) = -x^2 - x \neq x^2 - x$. ✗
4. Therefore $p$ is **neither even nor odd**.

### Practice Question

Let $f(x) = \dfrac{\sqrt{x - 1}}{x^2 - 9}$.

**(a)** Determine the **natural domain** of $f$, accounting for both the square root and the denominator restriction. Express your answer in interval notation.

**(b)** Evaluate $f(5)$ and $f(10)$, showing full substitution.

**(c)** Determine whether $f$ is even, odd, or neither. Justify algebraically.


## Composition and Inverse of Functions

## 4.1 Composition of Functions

Given $f: A \to B$ and $g: B \to C$, the **composite function** $g \circ f$ (read "$g$ composed with $f$") is defined as:

$$(g \circ f)(x) = g(f(x)), \quad x \in \text{dom}(f)$$

The output of $f$ becomes the input of $g$. The domain of $g \circ f$ is:

$$\text{dom}(g \circ f) = \{x \in \text{dom}(f) \mid f(x) \in \text{dom}(g)\}$$

**Important:** Composition is generally **not commutative**: $f \circ g \neq g \circ f$ in general.

## 4.2 Inverse Functions

If $f: A \to B$ is **bijective**, its **inverse function** $f^{-1}: B \to A$ satisfies:

$$f^{-1}(f(x)) = x \quad \forall x \in A \qquad \text{and} \qquad f(f^{-1}(y)) = y \quad \forall y \in B$$

Equivalently: $(f^{-1} \circ f)(x) = x$ (the identity on $A$) and $(f \circ f^{-1})(y) = y$ (the identity on $B$).

### Procedure to Find $f^{-1}(x)$:

1. Write $y = f(x)$.
2. Algebraically solve for $x$ in terms of $y$.
3. Swap the variable names: replace $y$ with $x$ (and $x$ with $y$).
4. The result is $f^{-1}(x)$.
5. Verify: confirm $f(f^{-1}(x)) = x$.

## 4.3 Graphical Relationship Between $f$ and $f^{-1}$

The graph of $f^{-1}$ is the **reflection** of the graph of $f$ across the line $y = x$. This is because swapping $x$ and $y$ corresponds geometrically to this reflection.

## 4.4 Restricting the Domain to Create an Inverse

If a function is not injective over its natural domain, we may **restrict the domain** to a subset on which it is injective, thereby enabling an inverse. For example, $f(x) = x^2$ is not injective on $\mathbb{R}$, but restricting to $[0, +\infty)$ yields the bijection $f: [0,+\infty) \to [0,+\infty)$ with inverse $f^{-1}(x) = \sqrt{x}$.

## Worked Example 1: Computing Composite Functions

**Given:** $f(x) = 2x + 3$ and $g(x) = x^2 - 1$.

Find **(a)** $(g \circ f)(x)$, **(b)** $(f \circ g)(x)$, and **(c)** $(g \circ f)(2)$.

**Solution for (a) — $g \circ f$:**

1. Substitute $f(x)$ into $g$:

$$(g \circ f)(x) = g(f(x)) = g(2x + 3) = (2x + 3)^2 - 1$$

2. Expand:

$$(2x+3)^2 - 1 = 4x^2 + 12x + 9 - 1 = 4x^2 + 12x + 8$$

**Solution for (b) — $f \circ g$:**

1. Substitute $g(x)$ into $f$:

$$(f \circ g)(x) = f(g(x)) = f(x^2 - 1) = 2(x^2 - 1) + 3 = 2x^2 + 1$$

**Comparison:** $4x^2 + 12x + 8 \neq 2x^2 + 1$, confirming $g \circ f \neq f \circ g$.

**Solution for (c):**

$$(g \circ f)(2) = 4(2)^2 + 12(2) + 8 = 16 + 24 + 8 = 48$$

## Worked Example 2: Finding and Verifying an Inverse Function

**Find the inverse of** $f(x) = \dfrac{3x - 2}{x + 1}$, state its domain, and verify.

**Solution:**

1. Write $y = \dfrac{3x - 2}{x + 1}$.

2. Solve for $x$. Multiply both sides by $(x + 1)$:

$$y(x + 1) = 3x - 2$$
$$xy + y = 3x - 2$$

3. Gather $x$-terms on one side:

$$xy - 3x = -2 - y$$
$$x(y - 3) = -(2 + y)$$

4. Divide by $(y - 3)$ (valid when $y \neq 3$):

$$x = \frac{-(2 + y)}{y - 3} = \frac{-y - 2}{y - 3}$$

5. Swap $x \leftrightarrow y$ to write the inverse:

$$f^{-1}(x) = \frac{-x - 2}{x - 3}$$

6. **Domain of $f^{-1}$:** $x \neq 3$, so $\text{dom}(f^{-1}) = \mathbb{R} \setminus \{3\}$.

7. **Verify** $f(f^{-1}(x)) = x$:

$$f\!\left(\frac{-x-2}{x-3}\right) = \frac{3\cdot\frac{-x-2}{x-3} - 2}{\frac{-x-2}{x-3} + 1}$$

 Numerator: $\dfrac{3(-x-2)}{x-3} - 2 = \dfrac{-3x-6 - 2(x-3)}{x-3} = \dfrac{-3x-6-2x+6}{x-3} = \dfrac{-5x}{x-3}$

 Denominator: $\dfrac{-x-2}{x-3} + 1 = \dfrac{-x-2+x-3}{x-3} = \dfrac{-5}{x-3}$

 Therefore:

$$f(f^{-1}(x)) = \frac{\frac{-5x}{x-3}}{\frac{-5}{x-3}} = \frac{-5x}{-5} = x \checkmark$$

### Practice Question

Let $f(x) = \sqrt{x - 2}$ (with domain $[2, +\infty)$) and $g(x) = x^2 + 2$.

**(a)** Find $(f \circ g)(x)$ and state its domain.

**(b)** Find $(g \circ f)(x)$ and simplify fully. State its domain.

**(c)** Find $f^{-1}(x)$. State the domain and range of $f^{-1}$.

**(d)** Verify your answer to (c) by confirming that $(f \circ f^{-1})(x) = x$ on the appropriate domain.


## Transformations of Functions and Applications

## 5.1 Graph Transformations

Given a base function $y = f(x)$, we can produce new functions by systematically modifying it. Understanding transformations allows you to sketch complex functions without computing large tables of values.

### Summary Table of Transformations

| Transformation | New Function | Effect on Graph |
|:---------------|:------------|:----------------|
| Vertical shift up by $k$ | $y = f(x) + k,\; k > 0$ | Graph moves up by $k$ units |
| Vertical shift down by $k$ | $y = f(x) - k,\; k > 0$ | Graph moves down by $k$ units |
| Horizontal shift right by $h$ | $y = f(x - h),\; h > 0$ | Graph moves right by $h$ units |
| Horizontal shift left by $h$ | $y = f(x + h),\; h > 0$ | Graph moves left by $h$ units |
| Vertical stretch by factor $a$ | $y = a\,f(x),\; a > 1$ | Graph stretches vertically |
| Vertical compression | $y = a\,f(x),\; 0 < a < 1$ | Graph compresses vertically |
| Reflection in $x$-axis | $y = -f(x)$ | Graph flips over $x$-axis |
| Reflection in $y$-axis | $y = f(-x)$ | Graph flips over $y$-axis |
| Horizontal stretch/compress | $y = f(bx)$ | Horizontal scale factor $\frac{1}{b}$ |

### 5.2 General Transformation Form

The fully general form combining all transformations is:

$$y = a\,f\bigl(b(x - h)\bigr) + k$$

where:
- $a$ controls **vertical** scaling and reflection
- $b$ controls **horizontal** scaling and reflection
- $h$ controls **horizontal** translation (phase shift)
- $k$ controls **vertical** translation

### 5.3 Application: Modelling with Functions

Functions are indispensable tools for modelling real-world phenomena. Examples include:

| Phenomenon | Function Type | Typical Form |
|:-----------|:-------------|:-------------|
| Projectile height | Quadratic | $h(t) = -\frac{1}{2}g t^2 + v_0 t + h_0$ |
| Population growth | Exponential | $P(t) = P_0 \cdot e^{rt}$ |
| Radioactive decay | Exponential (decay) | $N(t) = N_0 \cdot e^{-\lambda t}$ |
| Electrical resistance (parallel) | Rational | $R = \frac{R_1 R_2}{R_1 + R_2}$ |
| Pendulum period | Square root | $T = 2\pi\sqrt{\frac{L}{g}}$ |

## Worked Example 1: Sketching via Transformations

**Describe the transformations applied to $y = x^2$ to obtain $y = -2(x + 3)^2 + 5$, and identify the vertex.**

**Solution:**

Rewrite in the form $y = a\,f(b(x-h)) + k$:

$$y = -2(x - (-3))^2 + 5$$

So $a = -2$, $b = 1$, $h = -3$, $k = 5$.

Apply transformations in order to the base parabola $y = x^2$:

1. **Horizontal shift left by 3:** $y = (x+3)^2$ — vertex moves from $(0,0)$ to $(-3, 0)$.
2. **Vertical stretch by factor 2:** $y = 2(x+3)^2$ — parabola becomes narrower.
3. **Reflection in $x$-axis** (since $a < 0$): $y = -2(x+3)^2$ — parabola opens downward.
4. **Vertical shift up by 5:** $y = -2(x+3)^2 + 5$ — vertex moves to $(-3, 5)$.

**Vertex:** $(-3, 5)$. **Opens:** downward. **Maximum value:** $5$ (attained at $x = -3$).

## Worked Example 2: Real-World Application — Projectile Motion

**A ball is thrown upward from a height of $2\,\text{m}$ with an initial velocity of $14\,\text{m/s}$. The height (in metres) at time $t$ seconds is:**

$$h(t) = -4.9t^2 + 14t + 2$$

**(a)** Find the maximum height reached.
**(b)** Find the time at which the ball hits the ground.

**Solution for (a) — Maximum Height:**

1. The function is quadratic with $a = -4.9 < 0$, so it has a maximum at the vertex.
2. The $t$-coordinate of the vertex:

$$t^* = -\frac{b}{2a} = -\frac{14}{2(-4.9)} = -\frac{14}{-9.8} = \frac{14}{9.8} \approx 1.429\,\text{s}$$

3. Substitute $t^* = \dfrac{10}{7}$ s exactly:

$$h\!\left(\frac{10}{7}\right) = -4.9\!\left(\frac{10}{7}\right)^2 + 14\!\left(\frac{10}{7}\right) + 2 = -4.9 \cdot \frac{100}{49} + 20 + 2$$

$$= -\frac{490}{49} + 22 = -10 + 22 = 12\,\text{m}$$

**Maximum height:** $12\,\text{m}$.

**Solution for (b) — Time to Hit Ground:**

1. Set $h(t) = 0$:

$$-4.9t^2 + 14t + 2 = 0$$

2. Multiply through by $-1$ and apply the quadratic formula:

$$t = \frac{-14 \pm \sqrt{14^2 - 4(4.9)(2)}}{2(-4.9)} = \frac{-14 \pm \sqrt{196 - 39.2}}{-9.8} = \frac{-14 \pm \sqrt{156.8}}{-9.8}$$

$$\sqrt{156.8} \approx 12.522$$

$$t = \frac{-14 + 12.522}{-9.8} \approx \frac{-1.478}{-9.8} \approx 0.151\,\text{s} \quad \text{(rejected — ball going up)}$$

$$t = \frac{-14 - 12.522}{-9.8} \approx \frac{-26.522}{-9.8} \approx 2.706\,\text{s}$$

**The ball hits the ground at approximately $t \approx 2.71\,\text{s}$.**

### Practice Question

The graph of $y = \sqrt{x}$ is transformed to produce the function:

$$g(x) = -3\sqrt{x - 4} + 1$$

**(a)** List, in order, the sequence of transformations applied to $y = \sqrt{x}$ to obtain $g(x)$.

**(b)** State the domain and range of $g(x)$.

**(c)** Find the $x$-intercept of $g(x)$ algebraically (set $g(x) = 0$ and solve for $x$).

**(d)** A company models its weekly profit (in thousands of dollars) by $P(w) = -2(w - 5)^2 + 18$, where $w$ is the number of weeks after launch. Determine the maximum profit and the week in which it occurs. Also find the range of weeks during which the company is profitable (i.e., $P(w) > 0$).


## Common Mistakes

- **Confusing 'range' with 'codomain':** Students often treat these as identical. The **codomain** is the set declared as the target of a function (e.g., $\mathbb{R}$), whereas the **range** (or image) is the subset of the codomain that is actually achieved by some input. For $f: \mathbb{R} \to \mathbb{R}$ with $f(x) = x^2$, the codomain is $\mathbb{R}$ but the range is $[0, +\infty)$. Conflating these leads to incorrect surjectivity conclusions.
- **Misapplying horizontal transformations:** For $y = f(x - h)$, students frequently shift the graph in the **wrong direction** — shifting left when they should shift right. Remember: $f(x - h)$ with $h > 0$ shifts **right** by $h$ (because you need a larger $x$ to produce the same output). A helpful mnemonic: the shift is **opposite** to the sign inside the argument. Similarly, $y = f(bx)$ compresses horizontally by $\frac{1}{b}$ (not stretches), which is counterintuitive.
- **Reversing the order in composite functions:** $(g \circ f)(x) = g(f(x))$ means $f$ is applied **first**, then $g$. A common error is to apply $g$ first. Always read $g \circ f$ from right to left: the rightmost function acts first. This mistake becomes especially consequential when computing domains of composites.
- **Forgetting that $\emptyset$ is a subset of every set:** By convention, $\emptyset \subseteq A$ for every set $A$. Students sometimes claim a set has fewer subsets than it actually does because they exclude the empty set. This also means the power set $\mathcal{P}(A)$ always contains $\emptyset$ as one of its $2^{|A|}$ elements.
- **Attempting to find the inverse of a non-bijective function without domain restriction:** Not every function has an inverse. Students sometimes mechanically apply the swap-and-solve procedure to a function like $f(x) = x^2$ (without domain restriction) and obtain $f^{-1}(x) = \sqrt{x}$, forgetting that this is only valid on the restricted domain $[0, +\infty)$. Always check injectivity before claiming an inverse exists, or explicitly state the domain restriction under which the inverse is defined.

---

# Quiz Set 1

### q1. Let $A = \{1, 2, 3, 4, 5\}$ and $B = \{3, 4, 5, 6, 7\}$. What is $A \cup B$?
*Difficulty: easy*

- **A)** $\{3, 4, 5\}$
- **B)** $\{1, 2, 3, 4, 5, 6, 7\}$ **(correct)**
- **C)** $\{1, 2, 6, 7\}$
- **D)** $\{1, 2, 3, 4, 5, 6, 7, 8\}$

**Explanation:** The **union** $A \cup B$ is the set of all elements that belong to $A$ **or** $B$ (or both), with no duplicates. Combining $\{1,2,3,4,5\}$ and $\{3,4,5,6,7\}$ and removing repeated elements gives:
$$A \cup B = \{1, 2, 3, 4, 5, 6, 7\}$$
Option A is $A \cap B$ (the intersection), option C is the symmetric difference $A \triangle B$, and option D introduces the spurious element $8$.

### q2. Which of the following correctly defines a **function** from set $X$ to set $Y$?
*Difficulty: easy*

- **A)** A relation in which every element of $Y$ is paired with at least one element of $X$.
- **B)** A relation in which every element of $X$ is paired with **exactly one** element of $Y$. **(correct)**
- **C)** A relation in which every element of $X$ is paired with **at least two** elements of $Y$.
- **D)** A relation in which some elements of $X$ may have no image in $Y$.

**Explanation:** By definition, a **function** $f: X \to Y$ is a relation that assigns to **each** element $x \in X$ **exactly one** element $f(x) \in Y$. The two key conditions are:
1. **Totality** — every element of the domain $X$ must be mapped.
2. **Uniqueness** — no element of $X$ maps to more than one element of $Y$.

Option A describes a surjection condition on $Y$ (not the definition of a function). Option C violates uniqueness. Option D violates totality.

### q3. Given the universal set $U = \{1, 2, 3, 4, 5, 6, 7, 8\}$ and $A = \{2, 4, 6, 8\}$, what is the complement $A^c$ (also written $A'$)?
*Difficulty: easy*

- **A)** $\{1, 3, 5, 7\}$ **(correct)**
- **B)** $\{2, 4, 6, 8\}$
- **C)** $\emptyset$
- **D)** $\{1, 2, 3, 4, 5, 6, 7, 8\}$

**Explanation:** The **complement** of $A$ with respect to $U$ is defined as:
$$A^c = U \setminus A = \{x \in U \mid x \notin A\}$$
Removing the even elements $\{2,4,6,8\}$ from $U = \{1,2,3,4,5,6,7,8\}$ leaves the odd elements $\{1,3,5,7\}$. Option B is $A$ itself, option C is the empty set, and option D is $U$ itself.

### q4. Consider the function $f: \mathbb{R} \to \mathbb{R}$ defined by $f(x) = x^2 - 4$. What is the **range** of $f$?
*Difficulty: medium*

- **A)** $\mathbb{R}$
- **B)** $[-4, +\infty)$ **(correct)**
- **C)** $[0, +\infty)$
- **D)** $(-\infty, 4]$

**Explanation:** The range is the set of all values $f(x)$ can attain. Since $x^2 \geq 0$ for all $x \in \mathbb{R}$, we have:
$$f(x) = x^2 - 4 \geq 0 - 4 = -4$$
The minimum value $-4$ is achieved at $x = 0$, and as $|x| \to \infty$, $f(x) \to +\infty$. Therefore:
$$\text{Range}(f) = [-4, +\infty)$$
Option A incorrectly includes values below $-4$. Option C corresponds to the range of $x^2$ itself (without the $-4$ shift). Option D is an inverted, incorrect bound.

### q5. Let $f(x) = 2x + 3$ and $g(x) = x^2 - 1$. What is the composite function $(g \circ f)(x)$?
*Difficulty: medium*

- **A)** $2x^2 - 2 + 3$
- **B)** $4x^2 + 12x + 8$ **(correct)**
- **C)** $2x^2 + 1$
- **D)** $4x^2 + 8$

**Explanation:** The composite $(g \circ f)(x)$ means $g\bigl(f(x)\bigr)$. Substituting $f(x) = 2x+3$ into $g$:

1. Replace the argument of $g$ with $f(x)$:
$$g(f(x)) = (f(x))^2 - 1 = (2x+3)^2 - 1$$
2. Expand the perfect square:
$$(2x+3)^2 = 4x^2 + 12x + 9$$
3. Subtract 1:
$$4x^2 + 12x + 9 - 1 = 4x^2 + 12x + 8$$

Note: $(f \circ g)(x) = 2(x^2-1)+3 = 2x^2+1$, which is option C — a common error when the order of composition is reversed.

### q6. Which of the following relations on $\{1, 2, 3\}$, expressed as a set of ordered pairs, **fails** to be a function from $\{1,2,3\}$ to $\{1,2,3\}$?
*Difficulty: medium*

- **A)** $R_1 = \{(1,2),(2,3),(3,1)\}$
- **B)** $R_2 = \{(1,1),(2,2),(3,3)\}$
- **C)** $R_3 = \{(1,3),(2,3),(3,3)\}$
- **D)** $R_4 = \{(1,2),(1,3),(2,1),(3,1)\}$ **(correct)**

**Explanation:** A relation is a function if and only if every domain element appears as a **first component exactly once** (uniqueness of image). Checking each option:

| Relation | Domain elements covered | Any element mapped twice? | Function? |
|:---------|:------------------------|:-------------------------:|----------:|
| $R_1$ | $1, 2, 3$ — each once | No | Yes |
| $R_2$ | $1, 2, 3$ — each once | No | Yes |
| $R_3$ | $1, 2, 3$ — each once | No | Yes |
| $R_4$ | $1$ appears **twice** | **Yes** | **No** |

$R_4$ maps $1 \mapsto 2$ **and** $1 \mapsto 3$, violating uniqueness. Hence $R_4$ is not a function.

### q7. Using **De Morgan's Law**, which expression is equivalent to $(A \cup B)^c$?
*Difficulty: medium*

- **A)** $A^c \cup B^c$
- **B)** $A \cap B$
- **C)** $A^c \cap B^c$ **(correct)**
- **D)** $(A \cap B)^c$

**Explanation:** **De Morgan's Laws** for sets state:
$$\boxed{(A \cup B)^c = A^c \cap B^c}$$
$$\boxed{(A \cap B)^c = A^c \cup B^c}$$

> A mathematician, like a painter or poet, is a maker of patterns.
> — G. H. Hardy

Intuitively, an element $x$ is **not** in $A \cup B$ if and only if it is **not** in $A$ **and** **not** in $B$, which is precisely $x \in A^c \cap B^c$. Option A is De Morgan's second law applied incorrectly (it equals $(A \cap B)^c$, not $(A \cup B)^c$).

### q8. A function $f: A \to B$ is called **bijective** if it is both injective (one-to-one) and surjective (onto). Let $f: \mathbb{R} \to \mathbb{R}$ be defined by $f(x) = x^3 - x$. Which of the following statements is **correct**?
*Difficulty: hard*

- **A)** $f$ is bijective because it is a polynomial function with domain $\mathbb{R}$.
- **B)** $f$ is injective but not surjective, since not every real number is in its range.
- **C)** $f$ is surjective but **not** injective, since distinct inputs can yield the same output. **(correct)**
- **D)** $f$ is neither injective nor surjective.

**Explanation:** **Surjectivity:** $f(x) = x^3 - x$ is a continuous function with $\lim_{x \to -\infty} f(x) = -\infty$ and $\lim_{x \to +\infty} f(x) = +\infty$. By the **Intermediate Value Theorem**, every real number $y$ is attained, so $f$ is surjective onto $\mathbb{R}$.

**Injectivity (failure):** Computing $f'(x)$:
$$f'(x) = 3x^2 - 1$$
Setting $f'(x) = 0$: $x = \pm\dfrac{1}{\sqrt{3}}$. Since $f$ has a local maximum and a local minimum, it is **not monotone** and therefore **not injective**. A concrete counterexample:
$$f(0) = 0, \quad f(1) = 1 - 1 = 0$$
Both $x = 0$ and $x = 1$ map to $0$, confirming $f$ is **not** one-to-one.

Therefore $f$ is surjective but not injective — option C is correct.

---

# Quiz Set 2

### q1. Let $A = \{x \in \mathbb{Z} : -2 \leq x < 4\}$. Which of the following correctly lists all elements of $A$?
*Difficulty: easy*

- **A)** $\{-2, -1, 0, 1, 2, 3\}$ **(correct)**
- **B)** $\{-2, -1, 0, 1, 2, 3, 4\}$
- **C)** $\{-1, 0, 1, 2, 3\}$
- **D)** $\{-2, -1, 0, 1, 2\}$

**Explanation:** The set-builder notation $\{x \in \mathbb{Z} : -2 \leq x < 4\}$ specifies all integers $x$ satisfying $-2 \leq x < 4$. The inequality is **inclusive** at $-2$ (so $-2$ is included) and **strict** at $4$ (so $4$ is excluded). Listing: $-2, -1, 0, 1, 2, 3$. Option B incorrectly includes $4$; option C incorrectly excludes $-2$; option D incorrectly excludes $3$.

### q2. Consider the universal set $U = \{1, 2, 3, 4, 5, 6, 7, 8\}$, with subsets $P = \{1, 3, 5, 7\}$ and $Q = \{2, 3, 6, 7\}$. What is $(P \cup Q)'$?
*Difficulty: easy*

- **A)** $\{3, 7\}$
- **B)** $\{1, 2, 4, 5, 6, 8\}$
- **C)** $\{4, 8\}$ **(correct)**
- **D)** $\{1, 2, 5, 6\}$

**Explanation:** First, compute the union:
$$P \cup Q = \{1, 2, 3, 5, 6, 7\}$$
The complement $(P \cup Q)'$ consists of all elements in $U$ **not** in $P \cup Q$:
$$U \setminus (P \cup Q) = \{1,2,3,4,5,6,7,8\} \setminus \{1,2,3,5,6,7\} = \{4, 8\}$$
Option A is $P \cap Q$; option B is $(P \cap Q)'$; option D is $(P \triangle Q)$ restricted incorrectly.

### q3. A function $f : A \to B$ is said to be **surjective** (onto) if and only if which condition holds?
*Difficulty: easy*

- **A)** Every element of $A$ maps to exactly one element of $B$.
- **B)** Distinct elements of $A$ always map to distinct elements of $B$, i.e., $f(x_1) = f(x_2) \Rightarrow x_1 = x_2$.
- **C)** For every $b \in B$, there exists at least one $a \in A$ such that $f(a) = b$. **(correct)**
- **D)** $f$ is both injective and surjective simultaneously.

**Explanation:** **Surjectivity** requires that the range of $f$ equals the entire codomain $B$. Formally:
$$\forall\, b \in B,\; \exists\, a \in A \text{ such that } f(a) = b$$
Option A describes what it means for $f$ to be a **well-defined function** (single-valued). Option B is the definition of **injectivity** (one-to-one). Option D defines a **bijection**.

### q4. Given $f(x) = \dfrac{2x + 1}{x - 3}$, what is the **natural domain** of $f$ as a subset of $\mathbb{R}$, and what is $f^{-1}(x)$?
*Difficulty: medium*

- **A)** Domain: $\mathbb{R} \setminus \{3\}$; $\;f^{-1}(x) = \dfrac{3x + 1}{x - 2}$ **(correct)**
- **B)** Domain: $\mathbb{R} \setminus \{2\}$; $\;f^{-1}(x) = \dfrac{3x + 1}{x - 2}$
- **C)** Domain: $\mathbb{R} \setminus \{3\}$; $\;f^{-1}(x) = \dfrac{x + 3}{2x - 1}$
- **D)** Domain: $\mathbb{R}$; $\;f^{-1}(x) = \dfrac{3x + 1}{x - 2}$

**Explanation:** **Domain:** The denominator $x - 3 = 0$ when $x = 3$, so the natural domain is $\mathbb{R} \setminus \{3\}$.

**Inverse:** Let $y = \dfrac{2x+1}{x-3}$. Solve for $x$:

1. Multiply both sides by $(x - 3)$:
$$y(x - 3) = 2x + 1$$
2. Expand and collect $x$-terms:
$$xy - 3y = 2x + 1 \implies xy - 2x = 3y + 1$$
3. Factor and isolate:
$$x(y - 2) = 3y + 1 \implies x = \frac{3y + 1}{y - 2}$$

Thus $f^{-1}(x) = \dfrac{3x + 1}{x - 2}$. The domain of $f$ is **not** all of $\mathbb{R}$ (eliminates D), and the denominator excluded in the domain is $3$, not $2$ (eliminates B).

### q5. If $n(A) = 12$, $n(B) = 9$, and $n(A \cup B) = 17$, then $n(A \cap B)$ equals:
*Difficulty: easy*

- **A)** $5$
- **B)** $4$ **(correct)**
- **C)** $8$
- **D)** $3$

**Explanation:** The **Principle of Inclusion-Exclusion** for two finite sets states:
$$n(A \cup B) = n(A) + n(B) - n(A \cap B)$$
Substituting the given values:
$$17 = 12 + 9 - n(A \cap B)$$
$$n(A \cap B) = 21 - 17 = 4$$

### q6. Let $f(x) = x^2 - 4$ and $g(x) = \sqrt{x + 6}$. Which of the following correctly expresses the **composite function** $(g \circ f)(x)$ and states its domain?
*Difficulty: medium*

- **A)** $(g \circ f)(x) = \sqrt{x^2 + 2}$; domain $\mathbb{R}$ **(correct)**
- **B)** $(g \circ f)(x) = \sqrt{x^2 - 4} + 6$; domain $x \geq 2$
- **C)** $(g \circ f)(x) = \sqrt{x^2 + 2}$; domain $x \leq -\sqrt{2}$ or $x \geq \sqrt{2}$
- **D)** $(g \circ f)(x) = x - 2$; domain $x \geq -6$

**Explanation:** By definition, $(g \circ f)(x) = g(f(x))$. Substituting $f(x) = x^2 - 4$ into $g$:
$$g(f(x)) = \sqrt{(x^2 - 4) + 6} = \sqrt{x^2 + 2}$$

**Domain analysis:** We require $x^2 + 2 \geq 0$. Since $x^2 \geq 0$ for all $x \in \mathbb{R}$, it follows that $x^2 + 2 \geq 2 > 0$ for **all real** $x$. Hence the domain is $\mathbb{R}$, confirming option A. Option C has the correct expression but an incorrect, unnecessarily restricted domain.

### q7. A function $f : \mathbb{R} \to \mathbb{R}$ is defined piecewise as:

$$f(x) = \begin{cases} x^2 - 1 & \text{if } x < 0 \\ 2x + 3 & \text{if } x \geq 0 \end{cases}$$

Which of the following statements about $f$ is **true**?
*Difficulty: medium*

- **A)** $f$ is continuous at $x = 0$ because both pieces yield the same value there.
- **B)** $f$ is **not** continuous at $x = 0$ because $\lim_{x \to 0^-} f(x) \neq f(0)$. **(correct)**
- **C)** $f(-3) = -3$ and $f(2) = 7$.
- **D)** $f$ is an even function since $f(-x) = f(x)$ for all $x$.

**Explanation:** Evaluate the one-sided limits and function value at $x = 0$:

| Expression | Value |
|:-----------|------:|
| $\lim_{x \to 0^-} f(x) = (0)^2 - 1$ | $-1$ |
| $f(0) = 2(0) + 3$ | $3$ |
| $\lim_{x \to 0^+} f(x) = 2(0) + 3$ | $3$ |

Since $\lim_{x \to 0^-} f(x) = -1 \neq 3 = f(0)$, the left-hand limit does **not** equal $f(0)$, so $f$ is **discontinuous** at $x = 0$. This confirms option B.

For option C: $f(-3) = (-3)^2 - 1 = 9 - 1 = 8 \neq -3$, so C is false.

For option D: $f(-1) = (-1)^2 - 1 = 0$ but $f(1) = 2(1)+3 = 5$, so $f$ is not even.

### q8. Let $A$, $B$, and $C$ be non-empty subsets of a universal set $U$. Using set algebra (De Morgan's laws and distributive laws), simplify the expression:
$$\left[(A \cup B)' \cap C\right] \cup \left[(A \cap B') \cap C\right]$$
*Difficulty: hard*

- **A)** $C \setminus (A \cap B)$, i.e., $\left(A' \cup B'\right) \cap C$ **(correct)**
- **B)** $A' \cap B' \cap C$
- **C)** $C \setminus B$, i.e., $B' \cap C$
- **D)** $(A \cup B) \cap C$

**Explanation:** > Mathematics is the language in which God has written the universe.
> — Galileo Galilei

Simplify step-by-step using standard set identities:

1. Apply **De Morgan's Law** to the first term: $(A \cup B)' = A' \cap B'$
$$\left[(A' \cap B') \cap C\right] \cup \left[(A \cap B') \cap C\right]$$

2. **Factor out** $B' \cap C$ using the distributive law:
$$= (B' \cap C) \cap (A' \cup A)$$
   Wait — factor more carefully. Factor out $\cap C$:
$$= \left[(A' \cap B') \cup (A \cap B')\right] \cap C$$

3. Factor $B'$ from the union inside the brackets:
$$= \left[B' \cap (A' \cup A)\right] \cap C$$

4. Since $A' \cup A = U$ (complement law):
$$= \left[B' \cap U\right] \cap C = B' \cap C$$

   Hmm — let me recheck option A vs C. With the distributive factoring above, the simplified result is $B' \cap C = C \setminus B$, which matches **option C**.

   However, re-examining option A: $C \setminus (A \cap B) = (A' \cup B') \cap C$, which equals $(A' \cap C) \cup (B' \cap C)$ — not the same as $B' \cap C$.

   **Correct answer is C**: The expression simplifies to $B' \cap C$.

   **Step-by-step summary:**
   - $(A' \cap B' \cap C) \cup (A \cap B' \cap C)$
   - $= B' \cap C \cap (A' \cup A)$
   - $= B' \cap C \cap U$
   $$= B' \cap C$$

   This is the set of elements in $C$ that are **not** in $B$, regardless of membership in $A$.

---

# Quiz Set 3

### q1. Which of the following correctly describes the **symmetric difference** $A \triangle B$ of two sets $A$ and $B$?
*Difficulty: easy*

- **A)** $A \triangle B = (A \cup B) \setminus (A \cap B)$ **(correct)**
- **B)** $A \triangle B = (A \cap B) \setminus (A \cup B)$
- **C)** $A \triangle B = A \cup B$
- **D)** $A \triangle B = A \cap B$

**Explanation:** The symmetric difference $A \triangle B$ consists of all elements that belong to exactly one of the two sets — either $A$ or $B$, but **not both**. This is precisely the union minus the intersection:
$$A \triangle B = (A \cup B) \setminus (A \cap B)$$
Equivalently, $A \triangle B = (A \setminus B) \cup (B \setminus A)$. Options B, C, and D describe the empty set (for B), the full union, and the intersection — none of which match the definition.

### q2. Let $f : \mathbb{R} \to \mathbb{R}$ be defined by $f(x) = \dfrac{x^2 - 4}{x - 2}$. Which statement **best** characterises $f$?
*Difficulty: medium*

- **A)** $f$ is identical to the linear function $g(x) = x + 2$ on all of $\mathbb{R}$.
- **B)** $f$ is a rational function with a removable discontinuity at $x = 2$; its natural domain is $\mathbb{R} \setminus \{2\}$. **(correct)**
- **C)** $f$ is undefined for all real $x$ because the denominator can be zero.
- **D)** $f$ has a vertical asymptote at $x = 2$ and is therefore not simplifiable.

**Explanation:** Factoring the numerator:
$$f(x) = \frac{(x-2)(x+2)}{x-2} = x + 2, \quad x \neq 2$$
The cancellation is valid **only** when $x \neq 2$, so the domain is $\mathbb{R} \setminus \{2\}$. The discontinuity at $x = 2$ is **removable** (a hole in the graph, not a vertical asymptote), because $\lim_{x \to 2} f(x) = 4$ exists even though $f(2)$ is undefined. Option A is incorrect because $f$ and $g(x) = x+2$ have different domains. Option D confuses a removable discontinuity with a vertical asymptote.

### q3. If $n(U) = 80$, $n(A) = 35$, $n(B) = 42$, and $n(A \cup B) = 65$, what is $n(A' \cap B')$ — the number of elements in the complement of $A \cup B$?
*Difficulty: easy*

- **A)** $12$
- **B)** $15$ **(correct)**
- **C)** $22$
- **D)** $18$

**Explanation:** By De Morgan's law, $A' \cap B' = (A \cup B)'$. Therefore:
$$n(A' \cap B') = n(U) - n(A \cup B) = 80 - 65 = 15$$
We can also verify $n(A \cap B)$ using the inclusion–exclusion principle:
$$n(A \cap B) = n(A) + n(B) - n(A \cup B) = 35 + 42 - 65 = 12$$
The answer to the question is $\boxed{15}$.

### q4. A function $f : A \to B$ is said to be **bijective** if and only if it satisfies which pair of conditions?
*Difficulty: easy*

- **A)** Every element of $B$ has at least one pre-image in $A$ (surjective), **and** every element of $A$ maps to at least two elements of $B$ (multi-valued).
- **B)** Every element of $B$ has **exactly one** pre-image in $A$ — equivalently, $f$ is both injective (one-to-one) and surjective (onto). **(correct)**
- **C)** $f$ is injective but not necessarily surjective.
- **D)** The domain $A$ and codomain $B$ are equal as sets.

**Explanation:** A **bijection** is a function that is simultaneously:
- **Injective (one-to-one):** $f(x_1) = f(x_2) \Rightarrow x_1 = x_2$ — distinct inputs yield distinct outputs.
- **Surjective (onto):** $\forall b \in B,\ \exists\, a \in A$ such that $f(a) = b$ — every element of the codomain is reached.

Together these guarantee each element of $B$ has **exactly one** pre-image in $A$, establishing a perfect one-to-one correspondence. Option D ($A = B$ as sets) is neither necessary nor sufficient for bijectivity.

### q5. Given $f(x) = 2x + 3$ and $g(x) = x^2 - 1$, evaluate the composite function $(g \circ f)(x)$ and determine its value at $x = -1$.
*Difficulty: medium*

- **A)** $(g \circ f)(x) = 4x^2 + 12x + 8$; value at $x = -1$ is $0$. **(correct)**
- **B)** $(g \circ f)(x) = 2x^2 + 1$; value at $x = -1$ is $3$.
- **C)** $(g \circ f)(x) = 4x^2 + 6x + 8$; value at $x = -1$ is $6$.
- **D)** $(g \circ f)(x) = 2(x^2 - 1) + 3$; value at $x = -1$ is $3$.

**Explanation:** The composite $(g \circ f)(x)$ means $g(f(x))$. Substitute $f(x)$ into $g$:

1. Compute $f(x)$:
$$f(x) = 2x + 3$$

2. Substitute into $g(u) = u^2 - 1$ where $u = 2x + 3$:
$$(g \circ f)(x) = (2x + 3)^2 - 1 = 4x^2 + 12x + 9 - 1 = 4x^2 + 12x + 8$$

3. Evaluate at $x = -1$:
$$(g \circ f)(-1) = 4(-1)^2 + 12(-1) + 8 = 4 - 12 + 8 = 0$$

Option D computes $f(g(x))$ — the **reverse** composition — which is a common error.

### q6. Consider the piecewise-defined function:
$$f(x) = \begin{cases} x^2 + 1, & x < 0 \\ 2x - 3, & x \geq 0 \end{cases}$$
Which of the following statements about $f$ is **correct**?
*Difficulty: medium*

- **A)** $f$ is continuous at $x = 0$ because both pieces are polynomial.
- **B)** $f$ is **discontinuous** at $x = 0$ because $\lim_{x \to 0^-} f(x) = 1$ while $f(0) = -3$. **(correct)**
- **C)** $f(0) = 1$ because we substitute $x = 0$ into the first piece.
- **D)** $f$ is an even function because both pieces are smooth.

**Explanation:** To assess continuity at $x = 0$, compute the one-sided limits and the function value:

| Quantity | Expression | Value |
|:---------|:-----------|------:|
| Left-hand limit | $\lim_{x \to 0^-}(x^2 + 1)$ | $1$ |
| $f(0)$ (right piece applies since $x \geq 0$) | $2(0) - 3$ | $-3$ |
| Right-hand limit | $\lim_{x \to 0^+}(2x - 3)$ | $-3$ |

Since $\lim_{x \to 0^-} f(x) = 1 \neq -3 = f(0)$, the **left-hand and right-hand limits disagree**, so $f$ has a **jump discontinuity** at $x = 0$. Option C incorrectly applies the first branch at $x = 0$; option A incorrectly concludes continuity from piecewise-polynomial structure alone.

### q7. Let $f : \mathbb{R} \to \mathbb{R}$ be defined by $f(x) = x^3 - 3x$. Determine all real values of $x$ for which $f$ is an **odd function criterion** holds, and identify which of the following correctly proves or disproves the oddness of $f$.
*Difficulty: medium*

- **A)** $f(-x) = -x^3 + 3x = -(x^3 - 3x) = -f(x)$ for all $x \in \mathbb{R}$; therefore $f$ is **odd**. **(correct)**
- **B)** $f(-x) = x^3 - 3x = f(x)$ for all $x \in \mathbb{R}$; therefore $f$ is **even**.
- **C)** $f(-x) = -x^3 + 3x \neq f(x)$ and $f(-x) \neq -f(x)$; therefore $f$ is **neither even nor odd**.
- **D)** $f$ is odd only on the interval $[-1, 1]$, not on all of $\mathbb{R}$.

**Explanation:** A function $f$ is **odd** if $f(-x) = -f(x)$ for **all** $x$ in its domain. Verify:

1. Substitute $-x$:
$$f(-x) = (-x)^3 - 3(-x) = -x^3 + 3x$$

2. Compute $-f(x)$:
$$-f(x) = -(x^3 - 3x) = -x^3 + 3x$$

3. Compare:
$$f(-x) = -x^3 + 3x = -f(x) \quad \forall\, x \in \mathbb{R}$$

Since the identity holds for **all** real $x$ — not just a subinterval — $f$ is odd on $\mathbb{R}$. Geometrically, the graph of an odd function has **180° rotational symmetry** about the origin.

### q8. **[Hard]** Let $A$, $B$, and $C$ be finite sets with the following cardinalities:
$$n(A) = 20,\quad n(B) = 25,\quad n(C) = 22$$
$$n(A \cap B) = 8,\quad n(B \cap C) = 10,\quad n(A \cap C) = 6,\quad n(A \cap B \cap C) = 3$$

Using the **Inclusion–Exclusion Principle**, determine $n(A \cup B \cup C)$.
*Difficulty: hard*

- **A)** $46$ **(correct)**
- **B)** $54$
- **C)** $67$
- **D)** $52$

**Explanation:** The three-set Inclusion–Exclusion Principle states:
$$n(A \cup B \cup C) = n(A) + n(B) + n(C)$$
$$- n(A \cap B) - n(B \cap C) - n(A \cap C)$$
$$+ n(A \cap B \cap C)$$

Substitute the given values step by step:

1. Sum of individual cardinalities:
$$20 + 25 + 22 = 67$$

2. Subtract pairwise intersections:
$$67 - 8 - 10 - 6 = 43$$

3. Add back the triple intersection:
$$43 + 3 = 46$$

Therefore:
$$n(A \cup B \cup C) = \boxed{46}$$

This principle corrects for **double-counting**: elements in pairwise intersections are subtracted once, but elements in the triple intersection are then over-subtracted and must be added back exactly once.
