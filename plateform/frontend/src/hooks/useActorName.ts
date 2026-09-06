import { useCallback, useEffect, useState } from "react";

const STORAGE_KEY = "aquapulse.actor_name";
const DEFAULT_ACTOR = "Demo Operator";

export function useActorName() {
  const [actorName, setActorName] = useState(DEFAULT_ACTOR);

  useEffect(() => {
    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored && stored.trim()) {
      setActorName(stored.trim());
    }
  }, []);

  const update = useCallback((value: string) => {
    const next = value.slice(0, 120);
    setActorName(next);
    window.localStorage.setItem(STORAGE_KEY, next);
  }, []);

  return { actorName: actorName.trim() || DEFAULT_ACTOR, setActorName: update, raw: actorName };
}
