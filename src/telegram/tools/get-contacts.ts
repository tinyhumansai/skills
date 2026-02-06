// Tool: telegram-get-contacts
// Get contacts/users with optional filtering.
import { getContacts } from '../db-helpers';

/**
 * Get contacts tool definition.
 */
export const getContactsToolDefinition: ToolDefinition = {
  name: 'telegram-get-contacts',
  description:
    'Get Telegram contacts and users. Can filter to show only saved contacts or search by name/username. ' +
    'Returns user profiles including status, premium status, and bot flag.',
  input_schema: {
    type: 'object',
    properties: {
      contacts_only: {
        type: 'string',
        description: 'Only return users who are saved contacts (true/false)',
        enum: ['true', 'false'],
      },
      search: { type: 'string', description: 'Search term to filter by name or username' },
      limit: {
        type: 'string',
        description: 'Maximum number of contacts to return (default: 50, max: 100)',
      },
      offset: { type: 'string', description: 'Number of contacts to skip for pagination' },
    },
    required: [],
  },
  execute(args: Record<string, unknown>): string {
    try {
      const contactsOnly = args.contacts_only === 'true';
      const search = args.search as string | undefined;
      const limit = Math.min(parseInt((args.limit as string) || '50', 10), 100);
      const offset = parseInt((args.offset as string) || '0', 10);

      const contacts = getContacts({ contactsOnly, search, limit, offset });

      // Format for readability
      const formattedContacts = contacts.map(contact => {
        const name = [contact.first_name, contact.last_name].filter(Boolean).join(' ') || 'Unknown';

        return {
          id: contact.id,
          name,
          first_name: contact.first_name,
          last_name: contact.last_name,
          username: contact.username,
          phone_number: contact.phone_number ? maskPhoneNumber(contact.phone_number) : null,
          is_bot: contact.is_bot === 1,
          is_premium: contact.is_premium === 1,
          is_contact: contact.is_contact === 1,
          status: contact.status,
        };
      });

      return JSON.stringify({
        success: true,
        count: formattedContacts.length,
        contacts: formattedContacts,
        has_more: formattedContacts.length === limit,
      });
    } catch (err) {
      return JSON.stringify({
        success: false,
        error: err instanceof Error ? err.message : String(err),
      });
    }
  },
};

/**
 * Mask phone number for privacy.
 */
function maskPhoneNumber(phone: string): string {
  if (phone.length <= 4) return phone;
  return phone.slice(0, 4) + '****' + phone.slice(-2);
}
