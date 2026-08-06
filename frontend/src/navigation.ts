export type Route = "my-work"|"campaigns"|"content"|"calendar"|"approvals"|"localization"|"analytics"|"brand"|"brand-kit"|"connections"|"admin";
export const NAV_ITEMS:{route:Route;label:string;icon:string}[]=[
 {route:"my-work",label:"My work",icon:"⌂"},{route:"campaigns",label:"Campaigns",icon:"◫"},{route:"content",label:"Content",icon:"✦"},{route:"calendar",label:"Calendar",icon:"◷"},{route:"approvals",label:"Approvals",icon:"✓"},{route:"localization",label:"Localization",icon:"◎"},{route:"analytics",label:"Analytics",icon:"↗"},{route:"brand",label:"Brand governance",icon:"◇"},{route:"brand-kit",label:"Brand Kit",icon:"◆"},{route:"connections",label:"Connections",icon:"⌁"},{route:"admin",label:"Admin",icon:"⚙"}
];
export function normalizeRoute(hash:string):Route{const route=hash.replace(/^#\/?/,"") as Route;return NAV_ITEMS.some(item=>item.route===route)?route:"my-work"}
