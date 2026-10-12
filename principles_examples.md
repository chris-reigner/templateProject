# Core Principles — Bad vs Good Examples

Companion to [`principles.md`](principles.md) §1 (Core Principles). Each principle shows a violation (❌) and its fix (✅).

These are teaching snippets: imports and domain classes such as `Order` or `User` are left out where they add nothing.

## Table of contents

- [S — Single Responsibility](#s--single-responsibility)
- [O — Open/Closed](#o--openclosed)
- [L — Liskov Substitution](#l--liskov-substitution)
- [I — Interface Segregation](#i--interface-segregation)
- [D — Dependency Inversion](#d--dependency-inversion)
- [DRY — Don't Repeat Yourself](#dry--dont-repeat-yourself)
- [KISS — Keep It Simple](#kiss--keep-it-simple)
- [YAGNI — You Aren't Gonna Need It](#yagni--you-arent-gonna-need-it)
- [Law of Demeter](#law-of-demeter)
- [Parameterization & Configuration](#parameterization--configuration)
- [Decorators](#decorators)

---

## S — Single Responsibility

> One class = one single reason to change.

SRP does **not** mean "one method per class". A class can have many methods as long as they all serve the same concern and change for the same reason:

```python
class SalesReport:
    def __init__(self, sales: list[float]) -> None:
        self._sales = sales

    def total(self) -> float:
        return sum(self._sales)

    def average(self) -> float:
        return self.total() / len(self._sales)

    def best_sale(self) -> float:
        return max(self._sales)


report = SalesReport([120.0, 80.0, 200.0])
report.total()
report.average()  # several methods on one object, SRP respected
```

All of these answer "what do the sales numbers say?", so they change only when the **business calculation rules** change.

The violation starts when methods belong to **different concerns**, each changed by a different person for a different reason:

| Method | Concern | Who asks for a change |
|---|---|---|
| `total()` | business calculation | finance: "exclude refunds" |
| `to_html()` | presentation | design: "use a table" / "add PDF" |
| `save()` | storage / I/O | ops: "save to S3 instead of disk" |

**Quick test:** describe the class in one sentence without "and".

**❌ Bad** — one class computes, formats, and saves: three reasons to change.

```python
class SalesReport:
    def __init__(self, sales: list[float]) -> None:
        self.sales = sales

    def total(self) -> float:
        return sum(self.sales)

    def to_html(self) -> str:
        return f"<h1>Total: {self.total()}</h1>"

    def save(self, path: str) -> None:
        with open(path, "w") as f:
            f.write(self.to_html())
```

**✅ Good** — each class has one job.

```python
class SalesReport:
    def __init__(self, sales: list[float]) -> None:
        self._sales = sales

    def total(self) -> float:
        return sum(self._sales)


class HtmlReportFormatter:
    def format(self, report: SalesReport) -> str:
        return f"<h1>Total: {report.total()}</h1>"


class FileWriter:
    def write(self, path: Path, content: str) -> None:
        path.write_text(content, encoding="utf-8")


def publish_report(
    report: SalesReport, formatter: HtmlReportFormatter, writer: FileWriter, path: Path
) -> None:
    writer.write(path, formatter.format(report))
```

Each piece stays small and changes for its own reason, and a small function keeps the call site simple.

---

## O — Open/Closed

> Open for extension, closed for modification.

**❌ Bad** — every new discount type means editing this function.

```python
def apply_discount(price: float, kind: str) -> float:
    if kind == "none":
        return price
    elif kind == "student":
        return price * 0.8
    elif kind == "black_friday":
        return price * 0.5
    raise ValueError(kind)
```

**✅ Good** — Strategy pattern: a new discount is a new class, and existing code stays untouched.

```python
from typing import Protocol


class Discount(Protocol):
    def apply(self, price: float) -> float: ...


class NoDiscount:
    def apply(self, price: float) -> float:
        return price


class PercentageDiscount:
    def __init__(self, rate: float) -> None:
        self._rate = rate

    def apply(self, price: float) -> float:
        return price * (1 - self._rate)


def final_price(price: float, discount: Discount) -> float:
    return discount.apply(price)
```

---

## L — Liskov Substitution

> A subclass must be substitutable for its parent class without breaking behavior.

**❌ Bad** — `Square` breaks `Rectangle`'s contract: code that sets the width and expects the height to stay the same gets a wrong result.

```python
class Rectangle:
    def __init__(self, width: float, height: float) -> None:
        self.width, self.height = width, height

    def set_width(self, width: float) -> None:
        self.width = width


class Square(Rectangle):
    def set_width(self, width: float) -> None:
        self.width = self.height = width  # surprise side effect


def stretch(rect: Rectangle) -> float:
    rect.set_width(10)
    return rect.width * rect.height  # Rectangle(2, 5) -> 50, Square(5, 5) -> 100 ❌
```

**✅ Good** — share an abstraction that never promises behavior a subtype can't keep.

```python
from dataclasses import dataclass
from typing import Protocol


class Shape(Protocol):
    def area(self) -> float: ...


@dataclass(frozen=True)
class Rectangle:
    width: float
    height: float

    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class Square:
    side: float

    def area(self) -> float:
        return self.side**2


def total_area(shapes: list[Shape]) -> float:
    return sum(shape.area() for shape in shapes)


total_area([Rectangle(2, 5), Square(3)])  # 10 + 9 = 19 ✅ any Shape is substitutable
```

**Why this works:**

- **The root cause was mutation.** `Rectangle` implicitly promised "`set_width()` leaves the height alone", and a `Square` can't keep that promise. Mathematically a square *is* a rectangle, but a *mutable* square is not a substitutable *mutable* rectangle.
- **`@dataclass(frozen=True)` removes the broken promise.** `@dataclass` generates `__init__`, `__repr__` and `__eq__`, and `frozen=True` makes instances immutable: `r.width = 10` raises `FrozenInstanceError`. To "change" a shape you create a new one (`dataclasses.replace(r, width=10)`), so there's no setter for a subtype to break.
- **`Square` no longer inherits from `Rectangle`.** They are siblings that both satisfy `Shape`. A `Protocol` is a structural contract: any class with `area() -> float` qualifies, and mypy checks it.
- **The contract is small enough to keep fully.** `Shape` promises only "I can tell you my area", so callers like `total_area` work with any implementation without surprises.

**Bonus:** since mutation was the problem, an immutable square *can* be a rectangle again. A factory is often the simplest (KISS) fix:

```python
@dataclass(frozen=True)
class Rectangle:
    width: float
    height: float

    def area(self) -> float:
        return self.width * self.height

    @classmethod
    def square(cls, side: float) -> "Rectangle":
        return cls(side, side)
```

**Takeaway:** Liskov isn't about real-world "is-a" relationships. It's about whether a subtype can keep **every promise** of its parent. Keep contracts small and avoid mutable state that subtypes would have to handle differently.

---

## I — Interface Segregation

> Prefer multiple specific interfaces over a single general-purpose one.

**ISP vs SRP:** they look at the problem from opposite sides.

| | SRP | ISP |
|---|---|---|
| Point of view | the **class that implements** the code | the **code that uses** the class |
| Question | "Does this class have one reason to change?" | "Is this caller forced to depend on methods it doesn't use?" |
| Applies to | the implementation | the interface (the type the caller asks for) |

The example below respects SRP but breaks ISP. The class is cohesive, but a caller sees far more of it than it needs.

```python
from typing import Protocol


class UserRepository(Protocol):
    def get(self, user_id: int) -> User: ...
    def list_all(self) -> list[User]: ...
    def save(self, user: User) -> None: ...
    def delete(self, user_id: int) -> None: ...


class SqlUserRepository:
    """Stores users in SQL. One responsibility: user persistence. SRP ✅"""

    def get(self, user_id: int) -> User: ...
    def list_all(self) -> list[User]: ...
    def save(self, user: User) -> None: ...
    def delete(self, user_id: int) -> None: ...
```

**❌ Bad** — a read-only service depends on the whole repository interface.

```python
class UserReportService:
    def __init__(self, repository: UserRepository) -> None:
        self._repository = repository

    def count_active(self) -> int:
        return sum(1 for user in self._repository.list_all() if user.is_active)
```

The service only calls `list_all()`, but:

1. **It has more power than it needs.** Nothing stops a future change from calling `delete()` inside a reporting service.
2. **Tests are heavier.** A fake must implement all four methods, or mypy rejects it:

   ```python
   class FakeRepository:
       def list_all(self) -> list[User]:
           return [User(active=True), User(active=False)]

       def get(self, user_id: int) -> User:
           raise NotImplementedError  # noise

       def save(self, user: User) -> None:
           raise NotImplementedError  # noise

       def delete(self, user_id: int) -> None:
           raise NotImplementedError  # noise
   ```

3. **It's coupled to changes it doesn't care about.** If `save()` gets a new parameter, the report service has to be rechecked.

**✅ Good** — each caller asks only for what it uses.

```python
class UserReader(Protocol):
    def list_all(self) -> list[User]: ...


class UserWriter(Protocol):
    def save(self, user: User) -> None: ...
    def delete(self, user_id: int) -> None: ...


class UserReportService:
    def __init__(self, reader: UserReader) -> None:
        self._reader = reader

    def count_active(self) -> int:
        return sum(1 for user in self._reader.list_all() if user.is_active)
```

- **The concrete class doesn't change.** `SqlUserRepository` already satisfies both `UserReader` and `UserWriter` structurally, so `UserReportService(SqlUserRepository(...))` still works.
- **Tests get small.** The fake needs one method:

  ```python
  class FakeReader:
      def list_all(self) -> list[User]:
          return [User(active=True), User(active=False)]


  assert UserReportService(FakeReader()).count_active() == 1
  ```

- **It's safe.** Through a `UserReader`, the service can't call `delete()`, and mypy flags any attempt.

**Rule of thumb:** a class follows SRP if you can describe it without "and". A caller follows ISP if it uses **every** method of the type it asks for. One class can implement several small interfaces.

---

## D — Dependency Inversion

> Depend on abstractions, not on concrete implementations.

**❌ Bad** — the service creates its own concrete dependency, so it is untestable without a real SMTP server and impossible to swap.

```python
class SignupService:
    def __init__(self) -> None:
        self._mailer = SmtpMailer("smtp.gmail.com", 587)

    def register(self, email: str) -> None:
        self._mailer.send(email, "Welcome!")
```

**✅ Good** — depend on an abstraction; the caller injects the implementation.

```python
class Mailer(Protocol):
    def send(self, to: str, body: str) -> None: ...


class SignupService:
    def __init__(self, mailer: Mailer) -> None:
        self._mailer = mailer

    def register(self, email: str) -> None:
        self._mailer.send(email, "Welcome!")


# production: SignupService(SmtpMailer(settings.smtp_host, settings.smtp_port))
# tests:      SignupService(Mock(spec=Mailer))
```

---

## DRY — Don't Repeat Yourself

> Any duplicated logic must be extracted into a reusable function, method, or class.

**❌ Bad** — the same validation is copy-pasted, and the copies drift apart the day one of them changes.

```python
def create_user(email: str) -> User:
    if "@" not in email or email.startswith("@"):
        raise ValueError("Invalid email")
    return User(email)


def update_email(user: User, email: str) -> None:
    if "@" not in email or email.startswith("@"):
        raise ValueError("Invalid email")
    user.email = email
```

**✅ Good** — the rule lives in one place.

```python
def validate_email(email: str) -> str:
    if "@" not in email or email.startswith("@"):
        raise ValueError("Invalid email")
    return email


def create_user(email: str) -> User:
    return User(validate_email(email))


def update_email(user: User, email: str) -> None:
    user.email = validate_email(email)
```

---

## KISS — Keep It Simple

> Favor the simplest solution that meets the need. One function = one clear, readable intent.

**❌ Bad** — flags, manual indexing, and redundant branches for a trivial task.

```python
def count_adults(ages: list[int]) -> int:
    count = 0
    i = 0
    while i < len(ages):
        is_adult = False
        if ages[i] >= 18:
            is_adult = True
        if is_adult == True:
            count = count + 1
        i += 1
    return count
```

**✅ Good** — one readable line that states the intent.

```python
def count_adults(ages: list[int], adult_age: int = 18) -> int:
    return sum(1 for age in ages if age >= adult_age)
```

### KISS ≠ fewest lines

KISS is about **how easy the code is to read**, not line count. A comprehension is simple when it reads like one sentence. Once it needs a second look, a loop or a named helper is simpler.

**✅ Good** — one loop, at most one filter, a short expression:

```python
active_emails = [user.email for user in users if user.is_active]
total = sum(order.amount for order in orders)
prices_by_id = {product.id: product.price for product in products}
```

**❌ Bad** — logic packed into one expression:

```python
result = [
    (o.id, sum(i.price * i.qty for i in o.items if not i.refunded))
    for c in customers
    if c.is_active
    for o in c.orders
    if o.status == "paid" and o.date.year == year
]
```

**✅ Good** — name the steps:

```python
def paid_orders(customer: Customer, year: int) -> list[Order]:
    return [o for o in customer.orders if o.status == "paid" and o.date.year == year]


def net_total(order: Order) -> float:
    return sum(item.price * item.qty for item in order.items if not item.refunded)


result = [
    (order.id, net_total(order))
    for customer in customers
    if customer.is_active
    for order in paid_orders(customer, year)
]
```

Other one-liners that hurt readability:

```python
# ❌ nested ternary
label = "high" if score > 80 else "medium" if score > 50 else "low"


# ✅ explicit
def score_label(score: int) -> str:
    if score > 80:
        return "high"
    if score > 50:
        return "medium"
    return "low"
```

```python
# ❌ comprehension used only for its side effect (builds a useless list)
[send_email(user) for user in users]

# ✅ a loop states the intent
for user in users:
    send_email(user)
```

```python
# ❌ chained lambdas
names = list(map(lambda u: u.name.title(), filter(lambda u: u.age >= 18, users)))

# ✅ comprehension
names = [user.name.title() for user in users if user.age >= 18]
```

**Rule of thumb:** use a comprehension when **all** of these are true:

- one `for` (two only if very obvious),
- at most one simple `if`,
- a short expression with no nested comprehension,
- you're **building a value**, not causing side effects,
- you can read it aloud as one sentence.

Otherwise, use a loop or extract a well-named helper function.

---

## YAGNI — You Aren't Gonna Need It

> Write only what is necessary for the current need. No "just in case" code.

**❌ Bad** — speculative parameters for features nobody asked for. They are dead branches that still need tests and maintenance.

```python
def export(
    rows: list[dict],
    path: Path,
    fmt: str = "csv",
    compress: bool = False,
    encrypt: bool = False,
    upload_to_s3: str | None = None,
) -> None:
    if fmt == "csv":
        ...
    elif fmt == "parquet":  # never used
        ...
    if compress:  # never used
        ...
```

**✅ Good** — exactly what the current need requires (CSV export).

```python
import csv
from pathlib import Path


def export_csv(rows: list[dict[str, str]], path: Path) -> None:
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=rows[0].keys())
        writer.writeheader()
        writer.writerows(rows)
```

---

## Law of Demeter

> An object should only talk to its "close friends". Avoid `a.b.c.d()` train wrecks.

**❌ Bad** — checkout reaches through order → customer → wallet and changes its internals.

```python
def checkout(order: Order) -> None:
    if order.customer.wallet.balance >= order.total:
        order.customer.wallet.balance -= order.total
```

**✅ Good** — each object hides its internals behind a high-level method.

```python
class Wallet:
    def __init__(self, balance: float) -> None:
        self._balance = balance

    def debit(self, amount: float) -> None:
        if amount > self._balance:
            raise ValueError("Insufficient funds")
        self._balance -= amount


class Customer:
    def __init__(self, wallet: Wallet) -> None:
        self._wallet = wallet

    def pay(self, amount: float) -> None:
        self._wallet.debit(amount)


def checkout(order: Order, customer: Customer) -> None:
    customer.pay(order.total)
```

### Why train wrecks are bad

The dots aren't the problem. The problem is that the caller has to know **how other objects are built inside**. In the bad example, `checkout` knows that an order has a customer, a customer has a wallet, a wallet has a balance, and how to change that balance safely.

1. **One internal change breaks callers far away.** If `Customer` replaces `wallet` with `payment_methods: list[PaymentMethod]`, every `x.customer.wallet...` in checkout, refunds, reports and scripts breaks. With `customer.pay(amount)`, only `Customer.pay()` changes.
2. **Business rules get bypassed and duplicated.** The "no overspending" check lives in the caller, so every other caller must copy it (DRY broken), and anyone who forgets can push the balance below zero:

   ```python
   order.customer.wallet.balance -= order.total  # forgot the check: negative balance 💥
   ```

   In the good version, the rule lives in `Wallet.debit()` and can't be skipped. This is **"Tell, don't ask"**: tell an object what to do and let it apply its own rules, instead of reading its data and deciding for it.
3. **Tests have to rebuild the whole object graph.**

   ```python
   # ❌ train wreck: fake the internals of three objects
   order = Mock()
   order.customer.wallet.balance = 100
   order.total = 30
   checkout(order)
   assert order.customer.wallet.balance == 70

   # ✅ encapsulated: fake one dependency
   customer = Mock(spec=Customer)
   checkout(Order(total=30), customer)
   customer.pay.assert_called_once_with(30)
   ```

4. **Every link can fail.** If `customer` or `wallet` is `None`, each caller must handle it or crash with `AttributeError: 'NoneType' object has no attribute 'wallet'`. A single `customer.pay()` handles it in one place.

**Close friends.** Inside a method, you can call methods on `self`, the method's parameters, objects the method creates, and `self`'s own attributes (one level). You shouldn't call methods on objects that those methods return.

**Chains that are fine.** The rule targets reaching into other objects' internals, not dots in general:

```python
name.strip().lower()  # ✅ same kind of value transformed step by step
Path("config") / "base.toml"  # ✅ value objects
query.filter(active=True).order_by(
    "name"
)  # ✅ fluent API returning the same kind of object
settings.api_base_url  # ✅ plain data object (config, DTO), no behavior to hide
```

| Train wreck | Encapsulated |
|---|---|
| Caller knows the internal structure | Caller knows one method |
| Rules duplicated in every caller | Rule lives in the object that owns the data |
| Refactoring breaks distant code | Refactoring stays local |
| Tests build deep mocks | Tests mock one dependency |

---

## Parameterization & Configuration

> No hardcoded environment-dependent values. Config is read only through a dedicated loader that returns a typed, immutable settings object injected at the entry point (`principles.md` §1.6).

**❌ Bad** — hardcoded path and threshold, plus a hidden environment read inside business logic.

```python
import os
from pathlib import Path


def find_large_files() -> list[Path]:
    root = Path("C:/Users/chris/data")  # environment-dependent
    limit = int(os.environ.get("MAX_MB", "100"))  # hidden config read
    return [p for p in root.rglob("*") if p.stat().st_size > limit * 1_000_000]
```

**✅ Good** — business logic is pure and parameterized; only the loader touches config and the environment.

```python
# template_project/settings.py — the ONLY place reading config files
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict, DirectoryPath, PositiveInt, SecretStr


class Settings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    data_dir: DirectoryPath  # must exist on disk
    max_file_mb: PositiveInt  # 0 or "abc" is rejected
    api_key: SecretStr  # masked in logs and repr


def get_environment(environ: Mapping[str, str]) -> str:
    return environ.get("APP_ENV", "local")


def read_toml(path: Path) -> dict[str, Any]:
    return tomllib.loads(path.read_text(encoding="utf-8"))


def load_config(
    environment: str, config_dir: Path, environ: Mapping[str, str]
) -> Settings:
    merged: dict[str, Any] = read_toml(config_dir / "base.toml") | read_toml(
        config_dir / f"{environment}.toml"
    )
    merged["api_key"] = environ.get("API_KEY")  # secret: env only, never in TOML
    return Settings.model_validate(merged)  # fails fast, lists every bad field
```

A broken configuration stops the app at startup with one clear message instead of crashing later, far from the cause:

```text
pydantic_core.ValidationError: 3 validation errors for Settings
data_dir
  Path does not point to a directory [input_value='C:/missing']
max_file_mb
  Input should be greater than 0 [input_value=0]
api_key
  Input should be a valid string [input_value=None]
```

```python
# business logic — no config read, values are injected
def find_large_files(root: Path, max_file_mb: int) -> list[Path]:
    limit_bytes = max_file_mb * 1_000_000
    return [
        p for p in root.rglob("*") if p.is_file() and p.stat().st_size > limit_bytes
    ]


# entry point — the only place touching os.environ; settings built once, values injected
def main() -> None:
    settings = load_config(get_environment(os.environ), Path("config"), os.environ)
    find_large_files(settings.data_dir, settings.max_file_mb)
```

---

## Decorators

> A decorator wraps a function to add behavior around it without touching its code (`principles.md` §2.1).

Decorators are for **cross-cutting concerns** (retry, logging, timing, caching, permission checks) that many functions need but that don't belong in business logic. They support:

- **SRP:** the function does its job, and the decorator handles the extra concern.
- **DRY:** the extra logic is written once and applied with one line.
- **Open/Closed:** behavior is added without modifying the function.

**❌ Bad** — retry logic copy-pasted into every network call, burying a one-line business action.

```python
def fetch_user(base_url: str, user_id: int) -> dict:
    for attempt in range(3):
        try:
            return requests.get(f"{base_url}/users/{user_id}", timeout=5).json()
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(1)


def fetch_orders(base_url: str, user_id: int) -> list[dict]:
    for attempt in range(3):  # same loop again
        try:
            return requests.get(f"{base_url}/orders?user={user_id}", timeout=5).json()
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(1)
```

**✅ Good** — the retry is written once and applied anywhere.

```python
import functools
import time
from collections.abc import Callable


def retry[**P, R](
    attempts: int, delay_seconds: float, exceptions: tuple[type[Exception], ...]
) -> Callable[[Callable[P, R]], Callable[P, R]]:
    """Retry the decorated function when it raises one of `exceptions`."""

    def decorator(func: Callable[P, R]) -> Callable[P, R]:
        @functools.wraps(func)  # keeps the name and docstring of func
        def wrapper(*args: P.args, **kwargs: P.kwargs) -> R:
            for attempt in range(1, attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions:
                    if attempt == attempts:
                        raise
                    time.sleep(delay_seconds)
            raise AssertionError("unreachable")

        return wrapper

    return decorator


def fetch_user(base_url: str, user_id: int) -> dict:
    return requests.get(f"{base_url}/users/{user_id}", timeout=5).json()


def fetch_orders(base_url: str, user_id: int) -> list[dict]:
    return requests.get(f"{base_url}/orders?user={user_id}", timeout=5).json()
```

Environment-dependent settings (attempts, delay) come from configuration, so the decorator is applied **at the entry point**, not with `@retry(attempts=3, ...)` above the definition. A `@` line runs at import time, before the settings are loaded, which would force hardcoded values (§1.6).

```python
def main() -> None:
    settings = load_config(get_environment(os.environ), Path("config"), os.environ)
    resilient = retry(
        attempts=settings.retry_attempts,
        delay_seconds=settings.retry_delay_seconds,
        exceptions=(requests.RequestException,),
    )
    resilient(fetch_user)(settings.api_base_url, 42)
    resilient(fetch_orders)(settings.api_base_url, 42)
```

The `@` syntax is fine when the arguments are **not** environment-dependent (e.g. `@functools.cache`, `@dataclass(frozen=True)`).

**How it works:** `@retry(...)` above `f` is shorthand for `f = retry(...)(f)`.

1. `retry(...)` takes the settings and returns `decorator`.
2. `decorator(func)` returns `wrapper`.
3. `wrapper` runs instead of the original and calls `func` inside the retry loop.

`[**P, R]` (Python 3.12+ generic syntax) keeps the original signature visible to mypy, and `functools.wraps` keeps the original name and docstring for logs and debugging.

**Why it matters:**

- **One place to fix.** Adding backoff or logging changes `retry` only.
- **Readable.** The decorator says *what happens around* the call, and the body says *what it does*.
- **Testable separately.** `retry` is tested once with a fake that fails twice then succeeds, and business functions are tested without retry noise.

**Decorators you already use:** `@dataclass`, `@classmethod`, `@property`, `@functools.cache`, `@pytest.fixture`.

**When not to use one:** if the behavior is specific to a single function, or changes its result in surprising ways, put it in the function itself. Decorators hide behavior, so keep them generic and predictable.
