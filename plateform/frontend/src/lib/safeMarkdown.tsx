import type { ReactNode } from "react";

function stripTags(value: string): string {
  return value.replace(/<[^>]*>/g, "");
}

function inlineMarkdown(text: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
  let last = 0;
  let match = pattern.exec(text);
  let index = 0;
  while (match) {
    if (match.index > last) {
      nodes.push(text.slice(last, match.index));
    }
    const token = match[0];
    if (token.startsWith("**")) {
      nodes.push(<strong key={`b-${index}`}>{token.slice(2, -2)}</strong>);
    } else if (token.startsWith("*")) {
      nodes.push(<em key={`i-${index}`}>{token.slice(1, -1)}</em>);
    } else {
      nodes.push(
        <code key={`c-${index}`} className="rounded bg-page px-1 text-[0.85em]">
          {token.slice(1, -1)}
        </code>,
      );
    }
    last = match.index + token.length;
    index += 1;
    match = pattern.exec(text);
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function SafeMarkdown({ text }: { text: string }) {
  const sanitized = stripTags(text).replace(/\[([^\]]+)\]\(([^)]+)\)/g, "$1");
  const blocks = sanitized.split(/\n{2,}/);
  return (
    <div className="space-y-2 text-sm text-ink">
      {blocks.map((block, blockIndex) => {
        const lines = block.split("\n").filter((line) => line.trim());
        const listItems = lines.filter((line) => /^[-*]\s+/.test(line));
        if (listItems.length === lines.length && lines.length > 0) {
          return (
            <ul key={blockIndex} className="list-disc space-y-1 pl-5">
              {listItems.map((line, lineIndex) => (
                <li key={lineIndex}>{inlineMarkdown(line.replace(/^[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={blockIndex} className="whitespace-pre-wrap">
            {inlineMarkdown(lines.join(" "))}
          </p>
        );
      })}
    </div>
  );
}
