// Generated from apps/api OpenAPI schema by scripts/generate_ts_types.py.
// Do not edit by hand.

export type TokenResponse = {
  "access_token": string;
  "token_type"?: string;
};
export type UserCreate = {
  "username": string;
  "password": string;
};
export type UserRead = {
  "username": string;
  "id": number;
  "disabled": boolean;
};
export type LaundryLoadRead = {
  "id": number;
  "created_at": number;
  "created_by": number;
  "label": string | null;
  "status": LaundryStatus;
  "washer_finish": number | null;
  "dryer_finish": number | null;
};
export type LaundryLoadCreate = {
  "label"?: string | null;
};
export type LaundryLoadUpdate = {
  "status"?: LaundryStatus | null;
  "label"?: string | null;
  "washer_duration_minutes"?: number | null;
  "dryer_duration_minutes"?: number | null;
};
export type IngredientRead = {
  "id": number;
  "name": string;
  "name_normalized": string;
  "category": IngredientCategory | null;
  "is_staple": boolean;
};
export type TagRead = {
  "id": number;
  "name": string;
  "name_normalized": string;
};
export type MakeableRecipe = {
  "recipe": RecipeRead;
  "missing_ingredients": IngredientRead[];
};
export type RecipeRead = {
  "id": number;
  "created_at": number;
  "updated_at": number;
  "created_by": number;
  "version": number;
  "name": string;
  "description": string | null;
  "prep_time_minutes": number | null;
  "cook_time_minutes": number | null;
  "source": string | null;
  "meal_type": MealType | null;
  "course": Course | null;
  "scale": string;
  "effective_yield": EffectiveYield;
  "ingredients": RecipeIngredientRead[];
  "steps": RecipeStepRead[];
  "tags": TagRead[];
};
export type RecipeCreate = {
  "name": string;
  "description"?: string | null;
  "prep_time_minutes"?: number | null;
  "cook_time_minutes"?: number | null;
  "source"?: string | null;
  "meal_type"?: MealType | null;
  "course"?: Course | null;
  "yield_quantity": string;
  "yield_unit": string;
  "ingredients"?: RecipeIngredientWrite[];
  "steps"?: RecipeStepWrite[];
  "tags"?: string[];
};
export type RecipeUpdate = {
  "name": string;
  "description"?: string | null;
  "prep_time_minutes"?: number | null;
  "cook_time_minutes"?: number | null;
  "source"?: string | null;
  "meal_type"?: MealType | null;
  "course"?: Course | null;
  "yield_quantity": string;
  "yield_unit": string;
  "ingredients"?: RecipeIngredientWrite[];
  "steps"?: RecipeStepWrite[];
  "tags"?: string[];
  "version": number;
};
export type SimilarRecipe = {
  "recipe": RecipeRead;
  "shared_count": number;
  "shared_ingredients": IngredientRead[];
};
export type LaundryStatus = "dirty" | "washing" | "drying" | "folding" | "done";
export type IngredientCategory = "produce" | "dairy" | "meat_seafood" | "bakery" | "pantry" | "canned" | "frozen" | "spices" | "condiments" | "beverages" | "snacks" | "baking" | "deli" | "other";
export type MealType = "breakfast" | "lunch" | "dinner" | "snack" | "dessert";
export type Course = "appetizer" | "main" | "side" | "drink" | "sauce";
export type EffectiveYield = {
  "quantity_display": string;
  "unit": string;
};
export type RecipeIngredientRead = {
  "ref_key": string;
  "ingredient": IngredientRead;
  "quantity_num": number | null;
  "quantity_den": number | null;
  "quantity_display": string | null;
  "unit": Unit | null;
  "preparation": string | null;
  "is_optional": boolean;
  "section": string | null;
  "position": number;
};
export type RecipeStepRead = {
  "position": number;
  "section": string | null;
  "text_template": string;
  "text_rendered": string;
};
export type RecipeIngredientWrite = {
  "ref_key": string;
  "ingredient"?: string | null;
  "ingredient_id"?: number | null;
  "quantity"?: string | null;
  "unit"?: Unit | null;
  "preparation"?: string | null;
  "is_optional"?: boolean;
  "section"?: string | null;
  "position": number;
};
export type RecipeStepWrite = {
  "text": string;
  "position": number;
  "section"?: string | null;
};
export type Unit = "g" | "kg" | "oz" | "lb" | "ml" | "l" | "tsp" | "tbsp" | "cup" | "fl_oz" | "piece" | "clove" | "slice" | "pinch" | "dash" | "to_taste";
