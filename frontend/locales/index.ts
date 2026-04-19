import { registerDicts } from "../lib/i18n";
import en from "./en";
import ko from "./ko";
import th from "./th";
import vi from "./vi";
import zh from "./zh";

registerDicts({ en, vi, th, zh, ko });

export { en, ko, th, vi, zh };
