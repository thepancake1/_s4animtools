from S4ClipThing.types.basic import uint16, uint32, string


class SlotAssignment(list):
    @staticmethod
    def deserialize(data, repeat):
        slot_assignments = []
        for i in range(repeat):
            idx = []
            for i in range(2):
                idx.append(uint16().deserialize(data))
           # print(idx)
            #print(data.tell())
            target_object_namespace_len, target_object_namespace = string().deserialize(data)
            target_joint_name_len, target_joint_name = string().deserialize(data)
            slot_assignment = SlotAssignment([*idx, target_object_namespace_len, target_object_namespace,
                                   target_joint_name_len, target_joint_name])
            slot_assignments.append(slot_assignment)
        return slot_assignments

    @staticmethod
    def space():
        return 0
