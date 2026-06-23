import type { Http } from "./http";
import type {
  LaundryLoadCreate,
  LaundryLoadRead,
  LaundryLoadUpdate,
} from "./generated";

const BASE = "/laundry/loads";

export interface LaundryClient {
  list(): Promise<LaundryLoadRead[]>;
  create(data: LaundryLoadCreate): Promise<LaundryLoadRead>;
  update(id: number, data: LaundryLoadUpdate): Promise<LaundryLoadRead>;
  remove(id: number): Promise<void>;
}

export function createLaundry(http: Http): LaundryClient {
  return {
    list() {
      return http.request<LaundryLoadRead[]>(BASE);
    },
    create(data) {
      return http.request<LaundryLoadRead>(BASE, {
        method: "POST",
        body: JSON.stringify(data),
      });
    },
    update(id, data) {
      return http.request<LaundryLoadRead>(`${BASE}/${id}`, {
        method: "PATCH",
        body: JSON.stringify(data),
      });
    },
    remove(id) {
      return http.request<void>(`${BASE}/${id}`, { method: "DELETE" });
    },
  };
}
