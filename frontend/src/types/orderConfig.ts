export type OrderMakerConfigData = {
  model: string;
  system_prompt: string;
  search_tool: string;
  set_request_tool: string;
  set_product_tool: string;
  search_row_template: string;
  search_empty_template: string;
  set_text_template: string;
  set_product_template: string;
  set_product_not_found_template: string;
  set_product_no_text_template: string;
  resolve_ambiguity_tool: string;
  resolve_ambiguity_template: string;
  resolve_ambiguity_none_template: string;
};
