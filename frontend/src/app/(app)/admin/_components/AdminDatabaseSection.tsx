"use client";

import { useState, useCallback, useRef } from "react";
import { Database, Play, Loader2, Clock, Rows3 } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { SectionHeader } from "./SectionHeader";
import { useExecuteQuery } from "@/hooks/api";
import type { AdminQueryResponse } from "@/types/admin";

const EXAMPLE_QUERIES = [
  "SELECT * FROM users LIMIT 20",
  "SELECT id, name, email FROM recipe LIMIT 20",
  "SELECT table_name FROM information_schema.tables WHERE table_schema = 'public'",
];

export function AdminDatabaseSection() {
  const [query, setQuery] = useState("");
  const [result, setResult] = useState<AdminQueryResponse | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const { mutate: executeQuery, isPending, error } = useExecuteQuery();

  const handleExecute = useCallback(() => {
    const trimmed = query.trim();
    if (!trimmed) return;

    executeQuery(trimmed, {
      onSuccess: (data) => setResult(data),
    });
  }, [query, executeQuery]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        handleExecute();
      }
    },
    [handleExecute],
  );

  const handleExampleClick = useCallback((sql: string) => {
    setQuery(sql);
    textareaRef.current?.focus();
  }, []);

  return (
    <div className="space-y-6">
      <SectionHeader
        icon={Database}
        title="Database Query"
        description="Execute read-only SQL queries against the production database."
      />

      {/* Query Input */}
      <Card>
        <CardContent className="p-4 space-y-3">
          <Textarea
            aria-label="Read-only SQL query"
            ref={textareaRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="SELECT * FROM users LIMIT 10"
            className="font-mono text-sm min-h-32 resize-y"
          />

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              Ctrl+Enter to execute. SELECT queries only (max 500 rows).
            </p>
            <Button
              onClick={handleExecute}
              disabled={isPending || !query.trim()}
            >
              {isPending ? (
                <Loader2 className="size-4 animate-spin" strokeWidth={1.5} />
              ) : (
                <Play className="size-4" strokeWidth={1.5} />
              )}
              {isPending ? "Running..." : "Execute"}
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Quick Examples */}
      <div className="flex flex-wrap gap-2">
        <span className="text-xs text-muted-foreground self-center">
          Examples:
        </span>
        {EXAMPLE_QUERIES.map((sql) => (
          <Badge
            key={sql}
            variant="secondary"
            className="cursor-pointer font-mono text-xs hover:bg-accent transition-colors"
            onClick={() => handleExampleClick(sql)}
          >
            {sql.length > 50 ? sql.slice(0, 50) + "..." : sql}
          </Badge>
        ))}
      </div>

      {/* Error */}
      {error && (
        <Card className="border-destructive">
          <CardContent className="p-4">
            <p className="text-sm text-destructive font-mono">
              {error.message}
            </p>
          </CardContent>
        </Card>
      )}

      {/* Results */}
      {result && (
        <Card>
          <CardContent className="p-4 space-y-3">
            {/* Stats bar */}
            <div className="flex items-center gap-4 text-xs text-muted-foreground">
              <span className="flex items-center gap-1">
                <Rows3 className="size-3.5" strokeWidth={1.5} />
                {result.row_count} row{result.row_count !== 1 ? "s" : ""}
              </span>
              <span className="flex items-center gap-1">
                <Clock className="size-3.5" strokeWidth={1.5} />
                {result.execution_time_ms}ms
              </span>
              <span>{result.columns.length} columns</span>
            </div>

            {/* Results table */}
            {result.columns.length > 0 ? (
              <div className="overflow-auto max-h-144 rounded-lg border border-border">
                <table className="w-full text-sm">
                  <thead className="sticky top-0 z-10">
                    <tr className="bg-muted">
                      {result.columns.map((col) => (
                        <th
                          key={col}
                          className="px-3 py-2 text-left font-medium text-muted-foreground whitespace-nowrap border-b border-border"
                        >
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {result.rows.map((row, i) => (
                      <tr
                        key={i}
                        className="border-b border-border last:border-b-0 hover:bg-muted/50 transition-colors"
                      >
                        {row.map((cell, j) => (
                          <td
                            key={j}
                            className="px-3 py-2 font-mono text-xs whitespace-nowrap max-w-80 truncate"
                            title={cell != null ? String(cell) : "NULL"}
                          >
                            {cell != null ? (
                              String(cell)
                            ) : (
                              <span className="text-muted-foreground italic">
                                NULL
                              </span>
                            )}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">
                Query executed successfully but returned no columns.
              </p>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
