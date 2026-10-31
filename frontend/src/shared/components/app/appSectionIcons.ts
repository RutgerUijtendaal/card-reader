import {
  Activity,
  Swords,
  Bell,
  BookOpen,
  ClipboardCheck,
  Folders,
  Gamepad2,
  Hammer,
  House,
  Settings,
  SlidersHorizontal,
  Upload,
} from 'lucide-vue-next';

export const APP_SECTION_ICONS = {
  home: House,
  encounters: Swords,
  decks: BookOpen,
  playtester: Gamepad2,
  myDecks: Folders,
  deckBuilder: Hammer,
  notifications: Bell,
  settings: SlidersHorizontal,
  imports: Upload,
  operations: Activity,
  review: ClipboardCheck,
  admin: Settings,
} as const;
