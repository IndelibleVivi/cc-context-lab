// Portable, opt-in context presentation rules. No model, filesystem or settings I/O.
// Runtime owners keep authorization, tool execution, recovery and delivery authority.
// Description pins identify reviewed prose fragments, never a Claude Code version.
// Unknown fragments and all parameter schemas remain with the native harness.
export const DESCRIPTION_RULES = Object.freeze([
  ['Agent', 'paragraph', '0650587e72250dbd80bfdf86d74f724e312e8f401e5c2d49d700798ad581dd95', ''],
  ['Agent', 'paragraph', 'd4de4bbc0816fc9f88dd1ee9e0ed896df05683132b63a9e584b391d958e459c2', ''],
  ['Agent', 'paragraph', '84d6b8b7d00d0d0015a550a41b9088060eb66b52dddffcafaf61cb8adf624b66', ''],
  ['Agent', 'paragraph', '679744b6807aafb2c024d692d3d55817edbd14efce2d5c309799a18fd0b3f12e', 'A fresh agent receives the prompt you supply.'],
  ['Agent', 'paragraph', 'e6e8ef65786405f8dcfe16b70c64a6f91136ed4253195c6f3cb2253077922a75', 'Forks and subagents run in the background. Completion arrives as a task notification; pending output is not a completed result.'],
  ['Bash', 'line', '97f84c4dce782ee438fcb2f3e67028d993b70975b6fbd8d1de78da00712527df', ''],
  ['Bash', 'line', '2d663710f19b43834933c20c8ca9588ec4776066460ac16406e1564f4936c903', '- GitHub @mentions in pull requests, issues and comments can notify the mentioned account.'],
  ['Bash', 'line', 'e756a970d2483f2b167c6e746845db6a29beed511eb05545e29b61a2c053d38e', ''],
  ['Bash', 'line', '55cdb5260d009ad401a2e4fe49983a4b91f92de2949cf420613edc636124a9b9', ''],
  ['Read', 'line', '135095686ed7e0430a409b32b12e00655b4b1c2868cf4f1449654a131f1a53cf', ''],
  ['Read', 'line', 'be3d3c6a50ae8ea1fa81b7673ed2ff84ad46761ac83edfe4fcdc7cfc023373bb', ''],
  ['Skill', 'paragraph', 'f245942d73fb1f9a7f8a2ff4757ccc8120d36530bcada0b12bccc4a20f206890', 'A skill loads packaged instructions, or runs a subagent and returns its result. A background skill returns an agent name first; its result arrives later as a task notification.'],
  ['WebSearch', 'line', '8b7baed98ee6fa79684498f000f301216b96aa8cfbfcc674795affb0f9b4e54f', '- Cite source URLs when the answer relies on search results.'],
].map(rule => Object.freeze(rule)));

export async function fragmentDigest(text) {
  const data = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text));
  return Array.from(new Uint8Array(data), byte => byte.toString(16).padStart(2, '0')).join('');
}

// undefined means pass through. Typed task results, safety notices, unknown
// engine attachments and hook/plugin content are never selected by this rule.
export function quietExtraAttachment(event) {
  if (event.origin?.kind === 'engine' && event.type === 'silent_turn_reminder'
      && typeof event.text === 'string') return { text: null };
}

export function quietContextBlocks(blocks) {
  if (!Array.isArray(blocks)) return blocks;
  return blocks.filter(block => block?.name !== 'userEmail');
}

export async function quietToolDescription(event, rules = DESCRIPTION_RULES) {
  if (event.provider?.plugin !== 'engine' || event.provider?.tier !== 'core'
      || typeof event.description !== 'string') return undefined;
  const selected = rules.filter(rule => rule[0] === event.tool);
  if (!selected.length) return undefined;
  let changed = false;
  const rewrite = async (text, unit) => {
    if (!text) return text;
    const candidates = selected.filter(rule => rule[1] === unit);
    if (!candidates.length) return text;
    const digest = await fragmentDigest(text);
    const rule = candidates.find(item => item[2] === digest);
    if (!rule) return text;
    changed = true;
    return rule[3];
  };
  const pieces = event.description.split(/(\n\n)/);
  for (let i = 0; i < pieces.length; i += 2) {
    const paragraph = await rewrite(pieces[i], 'paragraph');
    const lines = paragraph.split('\n');
    for (let j = 0; j < lines.length; j++) lines[j] = await rewrite(lines[j], 'line');
    pieces[i] = lines.join('\n');
  }
  if (!changed) return undefined;
  // Keep separators and unknown whitespace byte-for-byte, including examples.
  return pieces.join('');
}
