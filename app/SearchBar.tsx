"use client";

import { useState, FormEvent } from "react";
import { usePathname, useRouter, useSearchParams } from "next/navigation";

type SearchBarProps = {
  initialPlayer?: string;
  initialTeam?: string;
  initialQuery?: string;
};

export default function SearchBar({
  initialPlayer = "",
  initialTeam = "",
  initialQuery = "",
}: SearchBarProps) {
  const router = useRouter();
  const pathname = usePathname();
  const currentSearchParams = useSearchParams();

  const [player, setPlayer] = useState(initialPlayer);
  const [team, setTeam] = useState(initialTeam);
  const [query, setQuery] = useState(initialQuery);

  function handleSubmit(e: FormEvent<HTMLFormElement>) {
    e.preventDefault();

    const params = new URLSearchParams(currentSearchParams.toString());

    if (player.trim()) {
      params.set("player", player.trim());
    } else {
      params.delete("player");
    }

    if (team.trim()) {
      params.set("team", team.trim());
    } else {
      params.delete("team");
    }

    if (query.trim()) {
      params.set("query", query.trim());
    } else {
      params.delete("query");
    }

    router.push(`${pathname}?${params.toString()}#search`);
  }

  function handleClear() {
    setPlayer("");
    setTeam("");
    setQuery("");
    router.push(`${pathname}#search`);
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="grid gap-3 lg:grid-cols-[1fr_1fr_1.4fr_auto_auto]"
    >
      <input
        type="text"
        value={player}
        onChange={(e) => setPlayer(e.target.value)}
        placeholder="Player"
        className="w-full rounded-xl border border-[#cddaea] bg-[#f8fbff] px-4 py-3 text-sm text-[#0f172a] outline-none transition focus:border-[#315c8d] focus:bg-white"
      />

      <input
        type="text"
        value={team}
        onChange={(e) => setTeam(e.target.value)}
        placeholder="Team"
        className="w-full rounded-xl border border-[#cddaea] bg-[#f8fbff] px-4 py-3 text-sm text-[#0f172a] outline-none transition focus:border-[#315c8d] focus:bg-white"
      />

      <input
        type="text"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Topic or keyword"
        className="w-full rounded-xl border border-[#cddaea] bg-[#f8fbff] px-4 py-3 text-sm text-[#0f172a] outline-none transition focus:border-[#315c8d] focus:bg-white"
      />

      <button
        type="submit"
        className="rounded-xl bg-[#16304d] px-5 py-3 text-sm font-semibold text-white transition hover:bg-[#1d3c5f]"
      >
        Search
      </button>

      <button
        type="button"
        onClick={handleClear}
        className="rounded-xl border border-[#cddaea] bg-white px-5 py-3 text-sm font-semibold text-[#16304d] transition hover:bg-[#eef4fb]"
      >
        Clear
      </button>
    </form>
  );
}