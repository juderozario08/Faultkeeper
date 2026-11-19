import * as Sentry from "@sentry/browser";
import "./style.css";

// The official Sentry SDK, pointed at Faultkeeper. Override with VITE_FAULTKEEPER_DSN.
Sentry.init({
  dsn: import.meta.env.VITE_FAULTKEEPER_DSN ?? "http://0996015a936e583a6b05b82ef974de86@localhost:8000/1",
  release: "buggy-shop@1.0.0",
  environment: "demo",
});

const API = import.meta.env.VITE_API_URL ?? "http://localhost:5175";

interface Product {
  id: string;
  name: string;
  price: number;
  stock: number;
}
interface CartLine {
  id: string;
  qty: number;
}

const cart: CartLine[] = [];
let products: Product[] = [];
const $ = <T extends HTMLElement>(sel: string) => document.querySelector<T>(sel)!;

function setStatus(text: string, kind: "ok" | "error" = "ok") {
  const el = $("#status");
  el.textContent = text;
  el.className = kind;
}

function renderCart() {
  const list = $("#cart");
  list.innerHTML = cart.length ? "" : "<li class='empty'>Empty</li>";
  for (const line of cart) {
    const product = products.find((p) => p.id === line.id)!;
    const li = document.createElement("li");
    li.textContent = `${line.qty} × ${product.name}: $${(product.price * line.qty).toFixed(2)}`;
    list.append(li);
  }
}

function addToCart(id: string) {
  const line = cart.find((l) => l.id === id);
  if (line) line.qty += 1;
  else cart.push({ id, qty: 1 });
  renderCart();
  setStatus(`Added ${id} to cart`);
}

async function loadProducts() {
  const response = await fetch(`${API}/products`);
  products = await response.json();
  const grid = $("#products");
  grid.innerHTML = "";
  for (const p of products) {
    const card = document.createElement("div");
    card.className = "card";
    card.innerHTML = `<h3>${p.name}</h3><p>$${p.price.toFixed(2)} · ${p.stock ? `${p.stock} in stock` : "out of stock"}</p>`;
    const button = document.createElement("button");
    button.textContent = "Add to cart";
    button.onclick = () => addToCart(p.id);
    card.append(button);
    grid.append(card);
  }
  renderCart();
}

async function postCheckout(body: unknown) {
  const response = await fetch(`${API}/checkout`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) throw new Error(`Checkout failed with HTTP ${response.status}`);
  return (await response.json()) as { order_id: number; total: number };
}

// ---- Deliberate bugs -------------------------------------------------------

function cartTotal(lines: { product?: Product; qty: number }[]) {
  // BUG: assumes every line has a product
  return lines.reduce((sum, line) => sum + line.product!.price * line.qty, 0);
}

const bugs: Record<string, () => void | Promise<void>> = {
  "null-price": () => {
    setStatus("Calculating total…");
    cartTotal([{ product: products[0], qty: 1 }, { qty: 2 }]);
  },
  promise: () => {
    // BUG: rejected promise nobody awaits
    void new Promise((_, reject) => setTimeout(() => reject(new Error("Payment provider timed out")), 50));
    setStatus("Contacting payment provider…");
  },
  reviews: async () => {
    const response = await fetch(`${API}/products/mouse/reviews`);
    if (!response.ok) throw new Error(`Could not load reviews (HTTP ${response.status})`);
  },
  coupon: async () => {
    await postCheckout({ cart: [{ id: "keyboard", qty: 1 }], coupon: "FREE" });
  },
  stock: async () => {
    await postCheckout({ cart: [{ id: "mouse", qty: 1 }] });
  },
  message: () => {
    Sentry.captureMessage("Inventory sync is lagging behind by 5 minutes", "warning");
    setStatus("Warning logged");
  },
};

document.querySelectorAll<HTMLButtonElement>("[data-bug]").forEach((button) => {
  button.addEventListener("click", () => {
    const run = bugs[button.dataset.bug!];
    // Async bugs surface as unhandled rejections, which the SDK captures automatically.
    void Promise.resolve().then(run).catch((error) => {
      setStatus(String(error.message ?? error), "error");
      throw error;
    });
  });
});

$("#checkout").addEventListener("click", async () => {
  try {
    const order = await postCheckout({ cart, coupon: $<HTMLInputElement>("#coupon").value.trim() || undefined });
    cart.length = 0;
    renderCart();
    setStatus(`Order #${order.order_id} placed, total $${order.total.toFixed(2)}`);
  } catch (error) {
    Sentry.captureException(error);
    setStatus((error as Error).message, "error");
  }
});

loadProducts().catch((error) => {
  setStatus("Could not reach the Buggy Shop API on :5175. Is docker compose running?", "error");
  Sentry.captureException(error);
});
