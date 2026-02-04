/**
 * htmlparser2 polyfill for V8 runtime.
 * gramjs uses this for HTML message parsing.
 * This is a minimal implementation that handles basic HTML.
 */

class Parser {
  constructor(handler) {
    this.handler = handler;
  }

  write(html) {
    this.parse(html);
  }

  end() {
    if (this.handler.onend) {
      this.handler.onend();
    }
  }

  parse(html) {
    let pos = 0;
    const len = html.length;

    while (pos < len) {
      const tagStart = html.indexOf('<', pos);

      if (tagStart === -1) {
        // No more tags, emit remaining text
        if (pos < len && this.handler.ontext) {
          this.handler.ontext(this.decodeEntities(html.substring(pos)));
        }
        break;
      }

      // Emit text before the tag
      if (tagStart > pos && this.handler.ontext) {
        this.handler.ontext(this.decodeEntities(html.substring(pos, tagStart)));
      }

      // Find the end of the tag
      const tagEnd = html.indexOf('>', tagStart);
      if (tagEnd === -1) {
        // Malformed HTML, treat rest as text
        if (this.handler.ontext) {
          this.handler.ontext(this.decodeEntities(html.substring(tagStart)));
        }
        break;
      }

      const tagContent = html.substring(tagStart + 1, tagEnd);

      if (tagContent.startsWith('/')) {
        // Closing tag
        const tagName = tagContent.substring(1).trim().toLowerCase();
        if (this.handler.onclosetag) {
          this.handler.onclosetag(tagName);
        }
      } else if (tagContent.startsWith('!--')) {
        // Comment - skip
        const commentEnd = html.indexOf('-->', tagStart);
        if (commentEnd !== -1) {
          pos = commentEnd + 3;
          continue;
        }
      } else {
        // Opening tag
        const selfClosing = tagContent.endsWith('/');
        const cleanContent = selfClosing ? tagContent.slice(0, -1) : tagContent;
        const parts = cleanContent.trim().split(/\s+/);
        const tagName = parts[0].toLowerCase();
        const attribs = {};

        // Parse attributes
        const attrString = cleanContent.substring(parts[0].length).trim();
        const attrRegex = /(\w+)(?:=(?:"([^"]*)"|'([^']*)'|(\S+)))?/g;
        let match;
        while ((match = attrRegex.exec(attrString)) !== null) {
          const attrName = match[1].toLowerCase();
          const attrValue = match[2] || match[3] || match[4] || '';
          attribs[attrName] = this.decodeEntities(attrValue);
        }

        if (this.handler.onopentag) {
          this.handler.onopentag(tagName, attribs);
        }

        if (selfClosing && this.handler.onclosetag) {
          this.handler.onclosetag(tagName);
        }
      }

      pos = tagEnd + 1;
    }
  }

  decodeEntities(text) {
    return text
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>')
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .replace(/&#39;/g, "'")
      .replace(/&nbsp;/g, ' ')
      .replace(/&#(\d+);/g, (_, code) => String.fromCharCode(parseInt(code, 10)))
      .replace(/&#x([0-9a-fA-F]+);/g, (_, code) => String.fromCharCode(parseInt(code, 16)));
  }
}

export { Parser };
export default { Parser };
