import { quietExtraAttachment, quietContextBlocks, quietToolDescription } from './quiet-rules.mjs';

export function register(on) {
  on('prompt.attachment', ($, event, next) => quietExtraAttachment(event) ?? next(event));
  on('prompt.context', async ($, event, next) => {
    const result = await next(event);
    const blocks = quietContextBlocks(result.blocks);
    return blocks === result.blocks || blocks.length === result.blocks.length ? result : { ...result, blocks };
  });
  on('tool.describe', async ($, event, next) => {
    const result = await next(event);
    const description = await quietToolDescription({ ...event, description: result.description });
    return description === undefined ? result : { ...result, description };
  });
}
