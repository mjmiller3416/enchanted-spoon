import { StatCard } from "recipe-app";
import { BookOpen, Heart, Flame, CalendarDays, ShoppingBasket, ChefHat } from "lucide-react";

// Dashboard stat tiles — one per chart-color preset, real Whiskful stats.
export const ColorPresets = () => (
  <div className="bg-background p-6 rounded-xl grid grid-cols-2 gap-4 max-w-2xl">
    <StatCard icon={BookOpen} value={42} label="Total Recipes" colorClass="purple" />
    <StatCard icon={Heart} value={12} label="Favorites" colorClass="pink" />
    <StatCard icon={CalendarDays} value={5} label="Meals Planned" colorClass="teal" />
    <StatCard icon={Flame} value={7} label="Day Streak" colorClass="amber" />
    <StatCard icon={ShoppingBasket} value={23} label="Shopping Items" colorClass="green" />
    <StatCard icon={ChefHat} value={94} label="Recipes Cooked" colorClass="indigo" />
  </div>
);

export const Loading = () => (
  <div className="bg-background p-6 rounded-xl grid grid-cols-2 gap-4 max-w-2xl">
    <StatCard icon={BookOpen} value={0} label="Total Recipes" colorClass="purple" isLoading />
    <StatCard icon={Heart} value={0} label="Favorites" colorClass="pink" isLoading />
  </div>
);
