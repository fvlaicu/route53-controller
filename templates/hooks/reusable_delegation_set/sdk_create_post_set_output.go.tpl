	if resp.DelegationSet != nil {
		ko.Status.ID = resp.DelegationSet.Id
	} else {
		ko.Status.ID = nil
	}
