import React, { useEffect, useState } from "react";

const API = import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const PAGE_SIZE = 20;

async function get(path, params = {}) {
  const url = new URL(path, API);
  for (const [key, value] of Object.entries(params)) {
    if (value !== "" && value !== null && value !== undefined) url.searchParams.set(key, value);
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`Request failed (${res.status})`);
  return res.json();
}

function useDebounced(value, delay = 350) {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const id = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(id);
  }, [value, delay]);
  return debounced;
}

function useApi(path, params = {}) {
  const [state, setState] = useState({ data: null, error: null, loading: true });
  const key = JSON.stringify([path, params]);
  useEffect(() => {
    let cancelled = false;
    setState((s) => ({ ...s, loading: true, error: null }));
    get(path, params)
      .then((data) => !cancelled && setState({ data, error: null, loading: false }))
      .catch((e) => !cancelled && setState({ data: null, error: e.message, loading: false }));
    return () => {
      cancelled = true;
    };
  }, [key]);
  return state;
}

function Pager({ total, offset, setOffset }) {
  const page = Math.floor(offset / PAGE_SIZE) + 1;
  const pages = Math.max(1, Math.ceil(total / PAGE_SIZE));
  return (
    <div className="pager">
      <button disabled={offset === 0} onClick={() => setOffset(Math.max(0, offset - PAGE_SIZE))}>
        Previous
      </button>
      <span>
        Page {page} of {pages} ({total} results)
      </span>
      <button disabled={page >= pages} onClick={() => setOffset(offset + PAGE_SIZE)}>
        Next
      </button>
    </div>
  );
}

function Sparkline({ values }) {
  const w = 240, h = 48, pad = 4;
  const min = Math.min(...values), max = Math.max(...values);
  const span = max - min || 1;
  const points = values.map((v, i) => {
    const x = values.length === 1 ? w / 2 : pad + (i * (w - 2 * pad)) / (values.length - 1);
    const y = max === min ? h / 2 : h - pad - ((v - min) / span) * (h - 2 * pad);
    return `${x},${y}`;
  });
  return (
    <svg width={w} height={h} role="img" aria-label="Price history chart">
      <polyline points={points.join(" ")} fill="none" stroke="currentColor" strokeWidth="2" />
    </svg>
  );
}

function PriceHistory({ book, onClose }) {
  const { data, error, loading } = useApi(`/books/${book.id}/price-history`);
  return (
    <aside className="panel">
      <button className="close" onClick={onClose} aria-label="Close">×</button>
      <h3>{book.title}</h3>
      {loading && <p>Loading price history…</p>}
      {error && <p className="error">{error}</p>}
      {data && (
        <>
          <Sparkline values={data.map((d) => d.price)} />
          <p>
            {data.length} price snapshot{data.length === 1 ? "" : "s"} · latest £{data[data.length - 1].price.toFixed(2)}
          </p>
          <a href={book.url} target="_blank" rel="noreferrer">View source page</a>
        </>
      )}
    </aside>
  );
}

function Stats() {
  const { data } = useApi("/stats");
  if (!data) return null;
  const cards = [
    ["Books tracked", data.books],
    ["Average price", `£${data.avg_price.toFixed(2)}`],
    ["Price range", `£${data.min_price.toFixed(2)} – £${data.max_price.toFixed(2)}`],
    ["In stock", data.in_stock],
  ];
  return (
    <div className="cards">
      {cards.map(([label, value]) => (
        <div className="card" key={label}>
          <span>{label}</span>
          <strong>{value}</strong>
        </div>
      ))}
    </div>
  );
}

function Books() {
  const [filters, setFilters] = useState({
    search: "", min_price: "", max_price: "", min_rating: "", in_stock: "", sort: "title", order: "asc",
  });
  const [offset, setOffset] = useState(0);
  const [selected, setSelected] = useState(null);
  const debounced = useDebounced(filters);
  const { data, error, loading } = useApi("/books", { ...debounced, limit: PAGE_SIZE, offset });

  const change = (name) => (e) => {
    setFilters({ ...filters, [name]: e.target.value });
    setOffset(0);
  };

  return (
    <section>
      <Stats />
      <div className="filters">
        <input placeholder="Search title…" value={filters.search} onChange={change("search")} />
        <input type="number" min="0" placeholder="Min £" value={filters.min_price} onChange={change("min_price")} />
        <input type="number" min="0" placeholder="Max £" value={filters.max_price} onChange={change("max_price")} />
        <select value={filters.min_rating} onChange={change("min_rating")}>
          <option value="">Any rating</option>
          {[1, 2, 3, 4, 5].map((n) => <option key={n} value={n}>{n}+ stars</option>)}
        </select>
        <select value={filters.in_stock} onChange={change("in_stock")}>
          <option value="">Any stock</option>
          <option value="true">In stock</option>
          <option value="false">Out of stock</option>
        </select>
        <select value={filters.sort} onChange={change("sort")}>
          <option value="title">Sort: title</option>
          <option value="price">Sort: price</option>
          <option value="rating">Sort: rating</option>
        </select>
        <select value={filters.order} onChange={change("order")}>
          <option value="asc">Ascending</option>
          <option value="desc">Descending</option>
        </select>
      </div>

      {error && <p className="error">Could not load books: {error}</p>}
      <div className="layout">
        <div className="table-wrap">
          <table>
            <thead>
              <tr><th>Title</th><th>Price</th><th>Rating</th><th>Stock</th></tr>
            </thead>
            <tbody>
              {data?.results.map((b) => (
                <tr key={b.id} onClick={() => setSelected(b)} className={selected?.id === b.id ? "active" : ""}>
                  <td>{b.title}</td>
                  <td>£{b.price.toFixed(2)}</td>
                  <td aria-label={`${b.rating} stars`}>{"★".repeat(b.rating || 0)}</td>
                  <td>{b.in_stock ? "In stock" : "Out"}</td>
                </tr>
              ))}
            </tbody>
          </table>
          {loading && <p className="muted">Loading…</p>}
          {data && data.results.length === 0 && <p className="muted">No books match these filters.</p>}
          {data && <Pager total={data.total} offset={offset} setOffset={setOffset} />}
        </div>
        {selected && <PriceHistory book={selected} onClose={() => setSelected(null)} />}
      </div>
    </section>
  );
}

function Quotes() {
  const [search, setSearch] = useState("");
  const [author, setAuthor] = useState("");
  const [offset, setOffset] = useState(0);
  const debouncedSearch = useDebounced(search);
  const authors = useApi("/quotes/authors");
  const { data, error, loading } = useApi("/quotes", { search: debouncedSearch, author, limit: PAGE_SIZE, offset });

  return (
    <section>
      <p className="muted">
        Scraped from a JavaScript-rendered page with Playwright (a plain HTTP request sees an empty page).
      </p>
      <div className="filters">
        <input
          placeholder="Search quotes…"
          value={search}
          onChange={(e) => { setSearch(e.target.value); setOffset(0); }}
        />
        <select value={author} onChange={(e) => { setAuthor(e.target.value); setOffset(0); }}>
          <option value="">All authors</option>
          {authors.data?.map((a) => <option key={a.author} value={a.author}>{a.author} ({a.quotes})</option>)}
        </select>
      </div>
      {error && <p className="error">Could not load quotes: {error}</p>}
      {loading && <p className="muted">Loading…</p>}
      <ul className="quotes">
        {data?.results.map((q) => (
          <li key={q.id}>
            <blockquote>“{q.text}”</blockquote>
            <cite>— {q.author}</cite>
            <div>{q.tags.map((t) => <span className="tag" key={t}>{t}</span>)}</div>
          </li>
        ))}
      </ul>
      {data && data.results.length === 0 && <p className="muted">No quotes match.</p>}
      {data && <Pager total={data.total} offset={offset} setOffset={setOffset} />}
    </section>
  );
}

export default function App() {
  const [tab, setTab] = useState("books");
  return (
    <main>
      <header>
        <h1>Data Pipeline Dashboard</h1>
        <nav>
          <button className={tab === "books" ? "on" : ""} onClick={() => setTab("books")}>Books</button>
          <button className={tab === "quotes" ? "on" : ""} onClick={() => setTab("quotes")}>Quotes</button>
        </nav>
      </header>
      {tab === "books" ? <Books /> : <Quotes />}
    </main>
  );
}
