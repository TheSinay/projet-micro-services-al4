import { describe, expect, it } from "vitest";

import { homePathForRole, isPathAllowedForRole, resolvePostLoginPath } from "@/lib/roles";

describe("homePathForRole", () => {
  it("mappe chaque rôle vers son accueil", () => {
    expect(homePathForRole("client")).toBe("/");
    expect(homePathForRole("restaurant_owner")).toBe("/restaurant/dashboard");
    expect(homePathForRole("courier")).toBe("/courier/dashboard");
  });
});

describe("isPathAllowedForRole", () => {
  it("limite le restaurateur à son espace", () => {
    expect(isPathAllowedForRole("/restaurant/dashboard", "restaurant_owner")).toBe(true);
    expect(isPathAllowedForRole("/orders", "restaurant_owner")).toBe(false);
  });

  it("limite le livreur à son espace", () => {
    expect(isPathAllowedForRole("/courier/dashboard", "courier")).toBe(true);
    expect(isPathAllowedForRole("/", "courier")).toBe(false);
  });

  it("autorise le client partout sauf les espaces professionnels", () => {
    expect(isPathAllowedForRole("/orders", "client")).toBe(true);
    expect(isPathAllowedForRole("/", "client")).toBe(true);
    expect(isPathAllowedForRole("/restaurant/dashboard", "client")).toBe(false);
    expect(isPathAllowedForRole("/courier/dashboard", "client")).toBe(false);
  });
});

describe("resolvePostLoginPath", () => {
  it("honore une origine autorisée", () => {
    expect(resolvePostLoginPath("client", "/orders")).toBe("/orders");
    expect(resolvePostLoginPath("restaurant_owner", "/restaurant/dashboard")).toBe(
      "/restaurant/dashboard",
    );
  });

  it("retombe sur l'accueil du rôle quand l'origine est absente ou interdite", () => {
    expect(resolvePostLoginPath("client", null)).toBe("/");
    expect(resolvePostLoginPath("courier", "/orders")).toBe("/courier/dashboard");
    expect(resolvePostLoginPath("client", "/login")).toBe("/");
  });
});
