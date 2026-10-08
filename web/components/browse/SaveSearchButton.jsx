"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { Button } from "@/components/ui/button";
import { clientApi } from "@/lib/client-api";

/** POST /saved-searches with the current filters. Sends signed-out users to /login. */
export function SaveSearchButton({ name, query, category, city, listingType, minPrice, maxPrice }) {
  const router = useRouter();
  const [state, setState] = useState({ busy: false, message: "", error: false });

  async function save() {
    setState({ busy: true, message: "", error: false });
    try {
      const body = { name, query: query || "" };
      if (category) body.category = category;
      if (city) body.city = city;
      if (listingType) body.listing_type = listingType;
      if (minPrice !== undefined && minPrice !== "") body.min_price = Number(minPrice);
      if (maxPrice !== undefined && maxPrice !== "") body.max_price = Number(maxPrice);
      await clientApi("/saved-searches", { method: "POST", body });
      setState({ busy: false, message: "Saved — we'll notify you about new matches.", error: false });
    } catch (err) {
      if (err.status === 401) {
        router.push("/login");
        return;
      }
      setState({ busy: false, message: err.message || "Could not save this search.", error: true });
    }
  }

  return (
    <div className="flex items-center gap-3">
      <Button type="button" variant="outline" onClick={save} disabled={state.busy}>
        {state.busy ? "Saving..." : "Save this search"}
      </Button>
      <p role="status" className={`text-sm ${state.error ? "text-destructive" : "text-success"}`}>
        {state.message}
      </p>
    </div>
  );
}
