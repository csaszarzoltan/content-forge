import {describe,expect,it} from "vitest";
import {campaignReadinessLabel, validationMessage} from "./flow";
describe("campaign flow helpers",()=>{
 it("explains empty readiness",()=>expect(campaignReadinessLabel(0)).toBe("Start by creating your first channel asset"));
 it("explains partial readiness",()=>expect(campaignReadinessLabel(50)).toBe("Resolve blockers to keep the campaign moving"));
 it("gives a friendly API recovery message",()=>expect(validationMessage(new Error("offline"))).toContain("kept your work"));
});
