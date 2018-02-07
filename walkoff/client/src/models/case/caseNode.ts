export class CaseNode {
	/**
	 * Name of execution element with potential prefix (items without a name will have some logic to fill it)
	 */
	name: string;
	/**
	 * ID of execution element
	 */
	id: string;
	/**
	 * Execution element type (e.g. workflow, condition
	 */
	type: string;
	/**
	 * Children nodes of this class type
	 */
	children: CaseNode[] = [];
}
